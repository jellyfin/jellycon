
import xbmcvfs
import xbmc
import base64
import re
from urlparse import urlparse

import threading
import httplib
import io
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from PIL import ImageFilter, Image, ImageOps

from .simple_logging import SimpleLogging
from .datamanager import DataManager
from .downloadutils import DownloadUtils
from .utils import getArt

PORT_NUMBER = 24276
log = SimpleLogging(__name__)

def get_image_links(url):

    download_utils = DownloadUtils()
    server = download_utils.getServer()
    if server is None:
        return []

    url = re.sub("(?i)limit=[0-9]+", "limit=4", url)
    url = url.replace("{ItemLimit}", "4")
    url = re.sub("(?i)SortBy=[a-zA-Z]+", "SortBy=Random", url)

    if not re.search('limit=', url, re.IGNORECASE):
        url += "&Limit=4"

    if not re.search('sortBy=', url, re.IGNORECASE):
        url += "&SortBy=Random"

    data_manager = DataManager()
    result = data_manager.GetContent(url)

    items = result.get("Items")
    if not items:
        return []

    art_urls = []
    for iteem in items:
        art = getArt(item=iteem, server=server)
        art_urls.append(art)

    return art_urls



def build_image(path):
    log.debug("build_image()")

    log.debug("Request Path : {0}", path)

    request_path = path[1:]

    if request_path == "favicon.ico":
        return []

    decoded_url = base64.b64decode(request_path)
    log.debug("decoded_url : {0}", decoded_url)

    image_urls = get_image_links(decoded_url)

    width, height = 500, 750
    collage = Image.new('RGB', (width, height), (5, 5, 5))

    cols = 2
    rows = 2
    thumbnail_width = int(width / cols)
    thumbnail_height = int(height / rows)
    size = thumbnail_width, thumbnail_height
    image_count = 0

    for art in image_urls:

        thumb_url = art.get("thumb")
        if thumb_url:
            url_bits = urlparse(thumb_url.strip())

            host_name = url_bits.hostname
            port = url_bits.port
            user_name = url_bits.username
            user_password = url_bits.password
            url_path = url_bits.path
            url_query = url_bits.query

            server = "%s:%s" % (host_name, port)
            url_full_path = url_path + "?" + url_query

            log.debug("Adding Image : {0} {1} {2}", image_count, server, url_full_path)

            conn = httplib.HTTPConnection(server)
            conn.request("GET", url_full_path)#"/emby/Items/32907/Images/Primary?maxHeight=635&tag=b06948152c2c1203ceedd66721a18f6f&quality=90")
            image_responce = conn.getresponse()
            image_data = image_responce.read()

            loaded_image = Image.open(io.BytesIO(image_data))

            image = ImageOps.fit(loaded_image, (size), method=Image.ANTIALIAS, bleed=0.0, centering=(0.5, 0.5))

            x = int(image_count % cols) * thumbnail_width
            y = int(image_count/cols) * thumbnail_height
            collage.paste(image, (x, y))

            del image_data
            del loaded_image
            del image

            image_count += 1

    del image_urls

    imgByteArr = io.BytesIO()
    collage.save(imgByteArr, format='JPEG')
    image_bytes = imgByteArr.getvalue()

    return image_bytes


class HttpImageHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        log_line = format % args
        log.debug(log_line)
        return

    def do_GET(self):
        log.debug("HttpImageHandler:do_GET()")
        self.serve_image()
        return

    def do_HEAD(self):
        log.debug("HttpImageHandler:do_HEAD()")
        self.send_response(200)
        self.end_headers()
        return

    def do_QUIT(self):
        log.debug("HttpImageHandler:do_QUIT()")
        self.send_response(200)
        self.end_headers()
        return

    def serve_image(self):

        image_bytes = build_image(self.path)

        self.send_response(200)
        self.send_header('Content-type', 'image/jpeg')
        self.send_header('Content-Length', str(len(image_bytes)))
        self.end_headers()
        self.wfile.write(image_bytes)


class HttpImageServerThread(threading.Thread):

    keep_running = True

    def __init__(self):
        threading.Thread.__init__(self)

    def stop(self):
        self.keep_running = False
        log.debug("HttpImageServerThread:stop called")
        try:
            conn = httplib.HTTPConnection("localhost:%d" % PORT_NUMBER)
            conn.request("QUIT", "/")
            conn.getresponse()
        except Exception as err:
            pass

    def run(self):
        log.debug("HttpImageServerThread:started")
        server = HTTPServer(('', PORT_NUMBER), HttpImageHandler)

        while self.keep_running:
            server.handle_request()

        log.debug("HttpImageServerThread:exiting")