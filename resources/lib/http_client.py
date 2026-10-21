'''
Minimal HTTP client built on the standard library.

Every widget on the Kodi home screen is a separate plugin call that starts a
fresh Python interpreter. Importing external http libraries like requests/urllib3
takes significant CPU processing time on low power devices (especially when several
widgets load at once), far longer than the request itself.
http.client is much cheaper to import and is all a single API call needs.
'''
from __future__ import (
    division, absolute_import, print_function, unicode_literals
)

import zlib

from six.moves import http_client
from six.moves.urllib.parse import urljoin, urlsplit

REDIRECT_CODES = (301, 302, 303, 307, 308)


def _ssl_context(verify_cert):
    import ssl
    if not verify_cert:
        return ssl._create_unverified_context()
    try:
        # Same CA bundle requests used, some platforms have no usable system store
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def open_url(method, url, headers=None, body=None, verify_cert=True,
             timeout=(5, 60), max_redirects=5):
    '''
    Send a request and follow redirects.

    timeout is (connect timeout, read timeout) in seconds.
    Returns the open http.client response: use .status, .getheader() and
    .read([size]), then .close() it.  The body is not decoded.
    Raises on connection errors.
    '''
    headers = dict(headers or {})
    connect_timeout, read_timeout = timeout
    for _ in range(max_redirects + 1):
        parts = urlsplit(url)
        if parts.scheme == 'https':
            conn = http_client.HTTPSConnection(
                parts.hostname, parts.port, timeout=connect_timeout,
                context=_ssl_context(verify_cert))
        else:
            conn = http_client.HTTPConnection(
                parts.hostname, parts.port, timeout=connect_timeout)

        target = parts.path or '/'
        if parts.query:
            target += '?' + parts.query

        try:
            conn.connect()
            conn.sock.settimeout(read_timeout)
            conn.request(method, target, body=body, headers=headers)
            response = conn.getresponse()
        except Exception:
            conn.close()
            raise
        # Like urllib: drop the connection's socket, the response keeps
        # reading from its own file object until it is closed
        if conn.sock:
            conn.sock.close()
            conn.sock = None

        location = response.getheader('Location')
        if response.status not in REDIRECT_CODES or not location:
            return response

        response.read()
        response.close()
        url = urljoin(url, location)
        # Like requests, never send credentials to another host
        if urlsplit(url).hostname != parts.hostname:
            headers = dict((k, v) for k, v in headers.items()
                           if k.lower() != 'authorization')
        if response.status == 303:
            method, body = 'GET', None

    raise IOError('Too many redirects: {}'.format(url))


def request(method, url, headers=None, body=None, verify_cert=True,
            timeout=(5, 60), max_redirects=5):
    '''
    Send a request, following redirects and decoding gzip/deflate bodies.

    timeout is (connect timeout, read timeout) in seconds.
    Returns (status_code, body_bytes).  Raises on connection errors.
    '''
    response = open_url(method, url, headers, body, verify_cert, timeout,
                        max_redirects)
    try:
        data = response.read()
    finally:
        response.close()

    encoding = (response.getheader('Content-Encoding') or '').lower()
    if encoding == 'gzip':
        data = zlib.decompress(data, 16 + zlib.MAX_WBITS)
    elif encoding == 'deflate':
        try:
            data = zlib.decompress(data)
        except zlib.error:
            data = zlib.decompress(data, -zlib.MAX_WBITS)

    return response.status, data
