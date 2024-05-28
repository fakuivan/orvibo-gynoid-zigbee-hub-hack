from shlex import quote as shq
from hashlib import md5
from typing import Literal, overload, TypeVar, TYPE_CHECKING
from collections.abc import Iterable, Iterator
from telnetlib import Telnet
from random import random
from pathlib import PurePosixPath as PPPath
import string

if TYPE_CHECKING:
    from hashlib import _Hash


def quote_args(*args) -> str:
    return " ".join(shq(str(arg)) for arg in args)


def command_sentinel() -> tuple[str, str]:
    """
    Provides a less fragile way to delimit command output,
    based on random and transformed sentinel values that are unlikely to
    naturally appear on the output
    """
    sentinel_pre = str(random())
    sentinel = md5(sentinel_pre.encode("ascii")).hexdigest() + "  -"
    return f"(printf %s '{sentinel_pre}' | md5sum)\r\n", sentinel


@overload
def wait_for_command(
    tn: Telnet, *args: str, timeout: float | None = None
) -> tuple[int, bytes]: ...


@overload
def wait_for_command(
    tn: Telnet,
    *,
    raw: str,
    timeout: float | None = None,
) -> tuple[int, bytes]: ...


def wait_for_command(
    tn: Telnet, *args: str, timeout: float | None = None, raw: str | None = None
) -> tuple[int, bytes]:
    s_command, sentinel = command_sentinel()
    command = (
        f"{quote_args(*args) if raw is None else raw}; \\\n"
        f"printf '\\n%03i' $?; {s_command}"
    ).encode("ascii")
    tn.write(command)
    tn.read_until(s_command.encode("ascii"), timeout=timeout)
    response = tn.read_until(sentinel.encode("ascii"), timeout=timeout)
    result = response[: -len(sentinel)]
    return int(result[-3:]), result[:-5]


def feed_from(hash: "_Hash", chunks: Iterable[bytes]) -> Iterator[bytes]:
    for chunk in chunks:
        hash.update(chunk)
        yield chunk


def printf_encode(blob: bytes) -> str:
    return repr(blob)[2:-1].replace("\\'", "'").replace("%", "%%").replace(" ", "\\x20")


def chunked(blob: bytes, chunk_size: int) -> Iterator[bytes]:
    for i in range(0, len(blob), chunk_size):
        yield blob[i : i + chunk_size]


T = TypeVar("T", bound=str)


def script(script: T) -> tuple[Literal["ash"], Literal["-c"], T]:
    return ("ash", "-c", script)


def pipe_binary(
    tn: Telnet, blob: Iterable[bytes], *command: str, timeout: float | None = None
) -> tuple[int, bytes]:
    """
    Pipes binary
    """
    s_command, sentinel = command_sentinel()
    # TODO: for some reason sometimes input gets mixed with the output and the last
    # `read` command is echoed back to the output.
    read_command = (
        'while read -sr chunk; do printf -- "$chunk"; done | \r\n'
        f"{quote_args(*command)}; \\\r\n"
        f"printf '\\n%03i' $?; {s_command}"
    ).encode(encoding="ascii")
    tn.write(read_command)
    tn.read_until(s_command.encode("ascii"), timeout=timeout)

    for chunk in blob:
        encoded = printf_encode(chunk).encode("ascii") + b"\n"
        tn.write(encoded)
    # Send EOF to signal `read` that this is the end of the data
    tn.write(b"\x04")

    result = tn.read_until(sentinel.encode("ascii"), timeout=timeout)[: -len(sentinel)]
    return int(result[-3:]), result[:-5]


class InvalidHashError(ValueError):
    pass


def upload_binary(
    tn: Telnet, blob: Iterable[bytes], dest: PPPath, timeout: float | None = None
) -> str:
    """
    Uploads binary via telnet to the `dest` path and returns the md5sum hash of
    the uploaded file.
    """
    code, message = pipe_binary(
        tn,
        blob,
        *script(f"set -euo pipefail; tee {shq(str(dest))} | md5sum"),
        timeout=timeout,
    )
    if code != 0:
        raise RemoteCommandError(
            code,
            message,
            f"Failed to upload and hash binary. Got code {code} with message {message}",
        )

    match message.split(b"  "):
        case (bytes(remote_hash), b"-\r\n"):
            # TODO: workaround for `read` issue in `pipe_binary`
            trimmed = remote_hash[-32:]
            if set(trimmed).issubset(string.hexdigits.encode()) and len(trimmed) == 32:
                return trimmed.decode().lower()
            raise InvalidHashError(
                f"Hex digest {trimmed} is not a valid hex string, "
                f"trimmed from {remote_hash}"
            )
        case _:
            raise InvalidHashError(
                f"md5sum command output does not follow expected format. Got: {message}"
            )


class RemoteCommandError(Exception):
    def __init__(self, code: int, output: bytes, message: str | None = None):
        super().__init__(
            message
            if message is not None
            else f"Failed to execute command, got code {code} with message:\n"
            f"{output}"
        )
        self.code = code
        self.output = output


def assert_command(result: tuple[int, bytes]) -> bytes:
    code, output = result
    if code == 0:
        return output
    raise RemoteCommandError(code, output)
