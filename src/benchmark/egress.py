"""Application URL policy plus an independent raw-socket enforcement layer."""

from __future__ import annotations

import ipaddress
import socket
import threading
from contextlib import AbstractContextManager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from types import TracebackType
from typing import Self
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit


class ContainmentViolation(ValueError):
    pass


@dataclass(frozen=True)
class Origin:
    scheme: str
    host: str
    port: int


class EgressPolicy:
    """Exact-origin policy for model-directed browser and form requests."""

    def __init__(
        self,
        allowed_base_urls: list[str],
        allowed_path_prefixes: list[str] | None = None,
    ) -> None:
        if not allowed_base_urls:
            raise ValueError("at least one allowed browser origin is required")
        self.origins = frozenset(self._origin(url) for url in allowed_base_urls)
        prefixes = allowed_path_prefixes or ["/"]
        if any(not prefix.startswith("/") for prefix in prefixes):
            raise ValueError("allowed browser path prefixes must be absolute")
        self.path_prefixes = tuple(
            prefix if prefix.endswith("/") else prefix + "/" for prefix in prefixes
        )

    def validate(self, target: str, current_url: str | None = None) -> str:
        if not target or any(character in target for character in ("\r", "\n", "\x00")):
            raise ContainmentViolation("malformed URL")
        if target.startswith("//"):
            raise ContainmentViolation("protocol-relative URL is forbidden")
        resolved = urljoin(current_url, target) if current_url else target
        parts = urlsplit(resolved)
        if parts.scheme != "http":
            raise ContainmentViolation("only HTTP is allowed on the local browser surface")
        if parts.username is not None or parts.password is not None:
            raise ContainmentViolation("URL credentials are forbidden")
        if "%" in parts.netloc or unquote(parts.netloc) != parts.netloc:
            raise ContainmentViolation("encoded host syntax is forbidden")
        if (
            "\\" in parts.path
            or "%" in parts.path
            or unquote(parts.path) != parts.path
            or any(segment == ".." for segment in parts.path.split("/"))
        ):
            raise ContainmentViolation("encoded or ambiguous path syntax is forbidden")
        origin = self._origin(resolved)
        if origin not in self.origins:
            raise ContainmentViolation("origin is not in the browser allowlist")
        normalized_path = parts.path or "/"
        path_for_match = normalized_path if normalized_path.endswith("/") else normalized_path + "/"
        if not any(path_for_match.startswith(prefix) for prefix in self.path_prefixes):
            raise ContainmentViolation("path is outside the benchmark trial scope")
        return urlunsplit((parts.scheme, parts.netloc, normalized_path, parts.query, ""))

    @staticmethod
    def _origin(url: str) -> Origin:
        parts = urlsplit(url)
        if parts.scheme != "http" or not parts.hostname:
            raise ContainmentViolation("allowed origins must be explicit HTTP URLs")
        try:
            port = parts.port or 80
        except ValueError as error:
            raise ContainmentViolation("invalid port") from error
        host = parts.hostname.rstrip(".").casefold()
        if host not in {"localhost", "127.0.0.1"}:
            try:
                address = ipaddress.ip_address(host)
            except ValueError as error:
                raise ContainmentViolation("pre-paid origins must be declared loopback hosts") from error
            if not address.is_loopback:
                raise ContainmentViolation("pre-paid origins must be loopback")
        return Origin(parts.scheme, host, port)


_SocketPolicy = tuple[frozenset[tuple[str, int]], frozenset[tuple[str, int]]]
_ACTIVE_SOCKET_POLICY: ContextVar[_SocketPolicy | None] = ContextVar(
    "ai_abyss_socket_policy", default=None
)
_ORIGINAL_GETADDRINFO = socket.getaddrinfo
_ORIGINAL_CONNECT = socket.socket.connect
_ORIGINAL_CONNECT_EX = socket.socket.connect_ex


def _check_socket_destination(policy: _SocketPolicy, host, port) -> None:
    allowed, allowed_ips = policy
    normalized_host = str(host).rstrip(".").casefold()
    try:
        normalized_port = int(port)
    except (TypeError, ValueError) as error:
        raise ContainmentViolation("socket port is invalid") from error
    if (normalized_host, normalized_port) in allowed:
        return
    try:
        address = str(ipaddress.ip_address(normalized_host))
    except ValueError:
        address = ""
    if (address, normalized_port) in allowed_ips:
        return
    raise ContainmentViolation("runtime socket barrier denied the destination")


def _guarded_getaddrinfo(host, port, *args, **kwargs):
    policy = _ACTIVE_SOCKET_POLICY.get()
    if policy is not None:
        _check_socket_destination(policy, host, port)
    return _ORIGINAL_GETADDRINFO(host, port, *args, **kwargs)


def _guarded_connect(sock, address):
    policy = _ACTIVE_SOCKET_POLICY.get()
    if policy is not None:
        if not isinstance(address, tuple) or len(address) < 2:
            raise ContainmentViolation("Unix and malformed socket destinations are forbidden")
        _check_socket_destination(policy, address[0], address[1])
    return _ORIGINAL_CONNECT(sock, address)


def _guarded_connect_ex(sock, address):
    policy = _ACTIVE_SOCKET_POLICY.get()
    if policy is not None:
        if not isinstance(address, tuple) or len(address) < 2:
            raise ContainmentViolation("Unix and malformed socket destinations are forbidden")
        _check_socket_destination(policy, address[0], address[1])
    return _ORIGINAL_CONNECT_EX(sock, address)


class RuntimeSocketBarrier(AbstractContextManager["RuntimeSocketBarrier"]):
    """Scoped, independent socket denial for the browser/tool permission domain.

    It guards DNS resolution and raw socket connect calls, so an application
    allowlist bypass still cannot create an undeclared outbound connection.
    Provider transport is intentionally not created inside this scope.
    """

    _patch_lock = threading.RLock()
    _active_contexts = 0

    def __init__(self, allowed_origins: set[tuple[str, int]]) -> None:
        self.allowed = {(host.rstrip(".").casefold(), port) for host, port in allowed_origins}
        self.allowed_ips: set[tuple[str, int]] = set()
        for host, port in self.allowed:
            if host == "localhost":
                self.allowed_ips.update({("127.0.0.1", port), ("::1", port)})
            else:
                try:
                    self.allowed_ips.add((str(ipaddress.ip_address(host)), port))
                except ValueError:
                    pass
        self._token: Token[_SocketPolicy | None] | None = None

    def __enter__(self) -> Self:
        if self._token is not None:
            raise RuntimeError("socket barrier cannot be re-entered")
        self._token = _ACTIVE_SOCKET_POLICY.set(
            (frozenset(self.allowed), frozenset(self.allowed_ips))
        )
        with self._patch_lock:
            if self._active_contexts == 0:
                socket.getaddrinfo = _guarded_getaddrinfo
                socket.socket.connect = _guarded_connect
                socket.socket.connect_ex = _guarded_connect_ex
            type(self)._active_contexts += 1
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._token is None:
            return
        _ACTIVE_SOCKET_POLICY.reset(self._token)
        self._token = None
        with self._patch_lock:
            type(self)._active_contexts -= 1
            if self._active_contexts == 0:
                socket.getaddrinfo = _ORIGINAL_GETADDRINFO
                socket.socket.connect = _ORIGINAL_CONNECT
                socket.socket.connect_ex = _ORIGINAL_CONNECT_EX
