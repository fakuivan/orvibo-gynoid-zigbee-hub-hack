#!/usr/bin/env python3
from telnetlib import Telnet
import re
from ipaddress import IPv4Address, IPv4Interface
from pathlib import Path, PurePosixPath as PPPath
import tarfile
from io import BytesIO, TextIOBase
from utils import (
    wait_for_command,
    assert_command,
    pipe_binary,
    chunked,
    script,
    upload_binary,
    RemoteCommandError,
    InvalidHashError,
    feed_from,
)
from jinja2 import Environment
from shlex import quote as shq
from collections.abc import Callable
from typing import NamedTuple, Annotated
import os.path
import typer

# only hashing program in device
from hashlib import md5


motd = (
    b"+---------------------+\r\n"
    # typo from original banner
    b"| Wellcome to MiniHub |\r\n"
    b"+---------------------+\r\n"
    b"# "
)


def mini_hub_log_in(
    tn: Telnet,
    username: str,
    password: str,
    hostname: str = "MiniHub",
    timeout: float = 10,
) -> bool:
    tn.read_until(f"{hostname} login: ".encode(), timeout)
    tn.write(f"{username}\n".encode())
    tn.read_until(b"Password: ", timeout)
    tn.write(f"{password}\n".encode())
    tn.read_until(b"\r\n", timeout)
    bad_login, _, _ = tn.expect([re.escape(motd), b"Login incorrect"], timeout)
    return bad_login == 0


DEFAULT_FIRST_IP = IPv4Address("192.168.0.200")
DEFAULT_USERNAME = "root"
DEFAULT_PASSWORD = "sidlee"
mod_dir = Path(__file__).resolve().parent / "mod"
assert mod_dir.is_dir()


def stop_boot_sequence(tn: Telnet, timeout: float | None = None):
    assert_command(
        wait_for_command(
            tn,
            raw="pkill rc.local -f && pkill -f wait_until_network_ready",
            timeout=timeout,
        )
    )


class FS(NamedTuple):
    jffs2_dir = PPPath("/mnt")
    mod_dir_name = PPPath("hack")
    mod_init_dir_name = PPPath("init")
    mod_bin_dir_name = PPPath("bin")
    new_mnt = PPPath("actually_mnt")
    dropbear_dir_name = PPPath("dropbear")

    @property
    def mod_dir(self) -> PPPath:
        return self.jffs2_dir / self.mod_dir_name

    @property
    def mod_init_dir(self) -> PPPath:
        return self.mod_dir / self.mod_init_dir_name

    @property
    def mod_bin_dir(self) -> PPPath:
        return self.mod_dir / self.mod_bin_dir_name

    @property
    def dropbear_dir(self) -> PPPath:
        return self.mod_dir / self.dropbear_dir_name


class SSH(NamedTuple):
    login_key: str
    proxy_key: str


class Config(NamedTuple):
    ssh: SSH
    ip_iface: IPv4Interface

    @property
    def ip_addr(self) -> IPv4Address:
        return self.ip_iface.ip

    @property
    def ip_netmask(self) -> IPv4Address:
        return self.ip_iface.netmask


def render_from(env: Environment) -> Callable[[TextIOBase], str]:
    return lambda template: env.from_string(template.read()).render()


def get_environment(fs: FS, config: Config):
    template_env = Environment()

    def relative_to(path: PPPath | str, anchor: PPPath | str) -> PPPath:
        path = PPPath(path)
        anchor = PPPath(anchor)
        base = PPPath(*os.path.commonprefix([path.parts, anchor.parts]))
        moves_up = len(anchor.parts) - len(base.parts)
        return PPPath(*(("..",) * moves_up), path.relative_to(base))

    def quote_filter(obj) -> str:
        acceptable_cls = (Path, IPv4Address, str, int, float, PPPath)
        if not isinstance(obj, acceptable_cls):
            raise TypeError(
                f"Valid types to quote are {acceptable_cls}, got {type(obj)}"
            )
        return shq(str(obj))

    template_env.filters["quote_sh"] = quote_filter
    template_env.filters["relative_to"] = relative_to
    template_env.globals = dict(fs=fs, config=config)
    return template_env


def fill_tarfile(tar_file: tarfile.TarFile, render: Callable[[TextIOBase], str]):
    for file in mod_dir.rglob("*"):
        path_rel = file.relative_to(mod_dir)
        info = tar_file.gettarinfo(file, str(path_rel))
        info.uid = info.gid = 0
        info.uname = info.gname = "root"
        if file.is_dir():
            info.type = tarfile.DIRTYPE
            tar_file.addfile(info)
            continue

        assert file.is_file(), "Only regular files and directories are supported"
        info.type = tarfile.REGTYPE
        if file.suffix != ".jinja2":
            with file.open("rb") as read_buff:
                tar_file.addfile(info, read_buff)
            continue

        info.name = str(path_rel.with_suffix(""))
        with file.open("r") as read_buff:
            rendered = BytesIO(render(read_buff).encode(read_buff.encoding))
            info.size = len(rendered.getvalue())
            tar_file.addfile(info, rendered)


def upload_mod(
    tn: Telnet,
    tar_bytes: BytesIO,
    base_dir: PPPath = PPPath("/tmp/hack"),
    script_name: str = "mod.sh",
    timeout: float | None = None,
):
    tar_file_path = base_dir.with_suffix(".tar.gz")
    hash = md5()

    hexdigest_local = upload_binary(
        tn, feed_from(hash, chunked(tar_bytes.getvalue(), 1024)), tar_file_path
    )
    assert hash.hexdigest() == hexdigest_local
    assert_command(
        wait_for_command(
            tn,
            *script(
                f"mkdir {shq(str(tar_file_path))} && "
                f"cd {shq(str(tar_file_path))} && "
                f"tar xzf ../{shq(tar_file_path.name)} && "
                f"chmod +x ./{shq(script_name)}"
            ),
            timeout=timeout,
        )
    )


def set_sysled(tn, on: bool = True, blink: bool = False, timeout: float | None = None):
    assert_command(
        wait_for_command(
            tn, "sysled", str(0 if not on else 2 if blink else 1), timeout=timeout
        )
    )


app = typer.Typer()


@app.command()
def build_tar(
    network_iface: Annotated[IPv4Interface, typer.Argument(parser=IPv4Interface)],
    ssh_login_key: str,
    ssh_proxy_key: str,
    output_file: typer.FileBinaryWrite,
):
    dev_config = Config(SSH(ssh_login_key, ssh_proxy_key), network_iface)
    env = get_environment(FS(), dev_config)
    with tarfile.open(mode="w|gz", fileobj=output_file) as tar_file:
        fill_tarfile(tar_file, render_from(env))


@app.command()
def telnet_pipe(
    input: typer.FileBinaryRead,
    command: list[str],
    ip: Annotated[IPv4Address, typer.Option(parser=IPv4Address)] = DEFAULT_FIRST_IP,
    port: int = 23,
    username: str = DEFAULT_USERNAME,
    password: str = DEFAULT_PASSWORD,
    timeout: float = 10,
):
    with Telnet(str(ip), port=port, timeout=timeout) as tn:
        mini_hub_log_in(tn, username, password)
        code, output = pipe_binary(
            tn, iter(lambda: input.read(1024), b""), *command, timeout=timeout
        )
        typer.echo(output)
        raise typer.Exit(code)


@app.command()
def telnet_upload(
    input: typer.FileBinaryRead,
    destination_path: Annotated[PPPath, typer.Argument(parser=PPPath)],
    ip: Annotated[IPv4Address, typer.Option(parser=IPv4Address)] = DEFAULT_FIRST_IP,
    port: int = 23,
    username: str = DEFAULT_USERNAME,
    password: str = DEFAULT_PASSWORD,
    timeout: float = 10,
):
    with Telnet(str(ip), port=port, timeout=timeout) as tn:
        mini_hub_log_in(tn, username, password)
        hash = md5()

        try:
            hexdigest_remote = upload_binary(
                tn,
                feed_from(hash, iter(lambda: input.read(1024), b"")),
                destination_path,
                timeout=timeout,
            )
        except InvalidHashError as e:
            typer.echo(f"Failed to recognize hash format: {e}", err=True)
            raise typer.Exit(2) from e
        except RemoteCommandError as e:
            typer.echo(f"Failed to upload and hash file: {e.output}", err=True)
            raise typer.Exit(e.code) from e

        hexdigest_local = hash.hexdigest()
        if hexdigest_local == hexdigest_remote:
            raise typer.Exit(0)
        typer.echo(f"Expected hash {hexdigest_local}, got {hexdigest_remote}", err=True)
        raise typer.Exit(1)


@app.command(
    help=f"""
    Stops the booting sequence by loggin into the hub via telnet and killing the init
    script.

    The hub will first look for a DHCP address for about 10 seconds while flashing the
    LED. If no DHCP server responds, it enters into a mode where it assigns itself the
    address {DEFAULT_FIRST_IP}, pings address .1 and then it continues increasing the
    third octate until it finds a gateway.
    We can make use of this first IP by quickly logging in and killing the init sequence
    before it changes to the next address.
    """
)
def stop_boot(
    ip: Annotated[IPv4Address, typer.Option(parser=IPv4Address)] = DEFAULT_FIRST_IP,
    port: int = 23,
    wait: Annotated[
        bool,
        typer.Option(
            "--wait",
            "-w",
            help="Prompts for a key press to then connect via telnet",
        ),
    ] = False,
    username: str = DEFAULT_USERNAME,
    password: str = DEFAULT_PASSWORD,
    timeout: float = 10,
):
    if wait:
        typer.pause(
            "Press any key 4 to 7 senconds after the hub LED stops blinking (blinks about 9 times)..."
        )
    with Telnet(str(ip), port=port, timeout=timeout) as tn:
        mini_hub_log_in(tn, username, password, timeout=timeout)
        stop_boot_sequence(tn, timeout)


if __name__ == "__main__":
    app()
