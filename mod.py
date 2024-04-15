from telnetlib import Telnet
import re
from ipaddress import IPv4Address, IPv4Interface
from pathlib import Path, PurePosixPath as PPPath
import tarfile
from io import BytesIO, TextIOBase
from utils import wait_for_command, assert_command, pipe_binary, chunked, script
from jinja2 import Template, Environment
from shlex import quote as shq
from collections.abc import Callable
from typing import NamedTuple
import os.path

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
mod_dir = Path(__file__).resolve().parent / "mod"
assert mod_dir.is_dir()


def stop_boot_sequence(tn: Telnet):
    assert_command(
        wait_for_command(
            tn, raw="pkill rc.local -f && pkill -f wait_until_network_ready"
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


def gen_tarfile(render: Callable[[TextIOBase], str]) -> BytesIO:
    # writes completely to ram then pushes, file is small so np
    tar_bytes = BytesIO()
    with tarfile.open(mode="w|gz", fileobj=tar_bytes) as tar_file:
        for file in mod_dir.rglob("*"):
            path_rel = file.relative_to(mod_dir)
            info = tarfile.TarInfo(str(path_rel)).replace(uid=0, gid=0)
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
                tar_file.addfile(
                    info, BytesIO(render(read_buff).encode(read_buff.encoding))
                )
    return tar_bytes


def upload_mod(tn: Telnet, tar_bytes: BytesIO, script_name: str = "mod.sh"):
    assert_command(
        pipe_binary(
            tn, chunked(tar_bytes.getvalue(), 1024), *script("cat > /tmp/hack.tar.gz")
        )
    )
    checksum, _ = assert_command(
        wait_for_command(tn, "md5sum", "/tmp/hack.tar.gz")
    ).split(b"  ", 2)
    assert md5(tar_bytes.getvalue()).hexdigest().encode() == checksum
    assert_command(
        wait_for_command(
            tn,
            *script(
                "mkdir /tmp/hack/ && "
                "cd /tmp/hack/ && "
                "tar xzf ../hack.tar.gz && "
                f"chmod +x ./{shq(script_name)}"
            ),
        )
    )


def set_sysled(tn, on: bool = True, blink: bool = False):
    assert_command(
        wait_for_command(tn, "sysled", str(0 if not on else 2 if blink else 1))
    )
