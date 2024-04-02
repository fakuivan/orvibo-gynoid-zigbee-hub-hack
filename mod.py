from telnetlib import Telnet
import re
import subprocess
import shlex


motd = (
    b"+---------------------+\r\n"
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


DEFAULT_FIRST_IP = "192.168.0.200"


def stop_boot_sequence(ip=DEFAULT_FIRST_IP):
    # wait for at least a single ping response
    print("Waiting for device to be up")
    subprocess.call(shlex.split(f"ping -i 0.1 {shlex.quote(ip)} -W 0 -c 1"))
    print("Device, up, logging in")
    with Telnet(ip) as tn:
        assert mini_hub_log_in(tn, "root", "sidlee")
        print("Logged in, stopping boot process")
        tn.write(
            b"sysled 0; pkill -f rc.local && pkill -f wait_until_network_ready && sysled 2; exit\r\n"
        )
        tn.read_all()
    print(f"Done. If led is blinking fast, you can connect to it at {ip}")
