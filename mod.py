from telnetlib import Telnet
import re
from ipaddress import IPv4Address
from pathlib import Path
import tarfile
from io import BytesIO
from utils import wait_for_command, assert_command, pipe_binary, chunked, script

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
mod_files = tuple(mod_dir / file for file in ("init/", "mod.sh", "serialgateway"))


def stop_boot_sequence(tn: Telnet):
    assert_command(
        wait_for_command(
            tn, raw="pkill rc.local -f && pkill -f wait_until_network_ready"
        )
    )


def upload_mod(tn: Telnet):
    def reset_file(info: tarfile.TarInfo):
        info.uid = 0
        info.gid = 0
        return info

    # writes completely to ram then pushes, file is small so np
    tar_bytes = BytesIO()
    with tarfile.open(mode="w|gz", fileobj=tar_bytes) as tar_file:
        for file in mod_files:
            tar_file.add(file, file.relative_to(mod_dir), filter=reset_file)

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
                "chmod +x ./mod.sh"
            ),
        )
    )
