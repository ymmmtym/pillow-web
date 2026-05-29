from urllib.parse import urlparse
import ipaddress
import socket


def is_private_ip(host):
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


def validate_background_image_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("httpもしくはhttpsのURLのみ許可されています")
    if not parsed.hostname:
        raise ValueError("URLにホスト名が含まれていません")
    if is_private_ip(parsed.hostname):
        raise ValueError("プライベートネットワークへのリクエストは許可されていません")
