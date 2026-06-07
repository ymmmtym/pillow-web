from __future__ import annotations

import ipaddress
import socket
from urllib.parse import ParseResult, urlparse

from pillow_web.exceptions import ValidationError


def is_private_ip(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        pass
    try:
        ips = socket.getaddrinfo(host, None)
        for addr in ips:
            ip = ipaddress.ip_address(addr[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                return True
    except (socket.gaierror, ValueError):
        pass
    return False


def validate_background_image_url(url: str) -> None:
    parsed: ParseResult = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValidationError("httpもしくはhttpsのURLのみ許可されています")
    if not parsed.hostname:
        raise ValidationError("URLにホスト名が含まれていません")
    if is_private_ip(parsed.hostname):
        raise ValidationError("プライベートネットワークへのリクエストは許可されていません")
