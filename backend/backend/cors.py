import os
from ipaddress import ip_address, ip_network
from urllib.parse import urlsplit

from django.http import HttpResponse


WEB_PORTS = {8081, 8082, 8083}
PRIVATE_NETWORKS = (
    ip_network('10.0.0.0/8'),
    ip_network('172.16.0.0/12'),
    ip_network('192.168.0.0/16'),
    ip_network('fc00::/7'),
)


def is_allowed_development_origin(origin):
    if not origin:
        return False

    try:
        parsed = urlsplit(origin)
        port = parsed.port
        host = parsed.hostname
    except ValueError:
        return False

    if (
        parsed.scheme != 'http'
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
        or port not in WEB_PORTS
    ):
        return False

    if host.lower() == 'localhost':
        return True

    try:
        address = ip_address(host)
    except ValueError:
        return False

    return address.is_loopback or any(address in network for network in PRIVATE_NETWORKS)


class DevelopmentCorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.configured_origins = {
            origin.strip()
            for origin in os.environ.get('DJANGO_CORS_ALLOWED_ORIGINS', '').split(',')
            if origin.strip()
        }

    def __call__(self, request):
        origin = request.headers.get('Origin')
        allowed_origin = origin in self.configured_origins or is_allowed_development_origin(origin)

        if request.method == 'OPTIONS' and allowed_origin:
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)

        if allowed_origin:
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'
            response['Vary'] = 'Origin'
        return response