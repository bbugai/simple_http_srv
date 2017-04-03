import socket
import argparse
import os
import re
import mimetypes
import sys
import io
import shutil
from urllib.request import url2pathname
from urllib.parse import unquote, quote


class Server(object):
    def __init__(self, port, request_handler):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(('', port))
        self.request_handler = request_handler

    def run_forever(self):
        self.socket.listen(1)
        while True:
            client_connection, client_address = self.socket.accept()
            request = client_connection.recv(4096)
            response = self.request_handler(client_connection, request).handle()
            response.flush()
            client_connection.close()


class RequestHandler(object):

    def __init__(self, connection, request):
        self.connection = connection
        self.wfile = connection.makefile('wb', 0)
        self.request = request

    def handle(self):
        index = None
        index_path = os.path.join(os.getcwd(), 'index.html')
        if os.path.isfile(index_path):
            index = open(index_path, 'rb')

        if index:
            return HttpResponse(self.wfile, 200, index, {'Content-Type': 'text/html'})
        else:
            matches = re.findall('^GET(.*)HTTP', self.request.decode())
            if matches:
                return self._serve_path(matches[0])

            return HttpResponse(self.wfile, 400, io.BytesIO(b'bad request'), headers={'Content-Type': 'text/html'})

    def _serve_path(self, url):
        url_path = url2pathname(url).strip()
        path = os.path.dirname(os.path.realpath(__file__)) + url_path
        if os.path.exists(path):
            if os.path.isdir(path):
                if not path.endswith('/'):
                    return HttpResponse(self.wfile, 301, headers={'Location': url_path + '/'})
                try:
                    directory_name = unquote(url_path, errors='surrogatepass')
                except UnicodeDecodeError:
                    directory_name = unquote(url_path)
                files = ''.join(
                    '<li><a href="{}">{}</a>'.
                        format(quote(p, errors='surrogatepass'),
                               unquote(p + '/' if os.path.isdir(p) else p, errors='surrogatepass'))
                    for p in sorted(os.listdir(path), key=lambda a: a.lower())
                )
                headers = {'Content-Type': 'text/html'}
                template = '<head><meta charset="{}"></head><h2>Directory listing for {}</h2><hr><ul>{}</ul><hr>'
                enc = sys.getfilesystemencoding()
                body = template.format(enc, directory_name, files).encode(enc, 'surrogatepass')
                f = io.BytesIO()
                f.write(body)
                f.seek(0)
                return HttpResponse(self.wfile, 200, f, headers)

            content_type, _ = mimetypes.guess_type(path)
            content_type = content_type or 'application/octet-stream'
            f = open(path, 'rb')
            headers = {'Content-Length': str(os.fstat(f.fileno())[6]), 'Content-Type': content_type}
            return HttpResponse(self.wfile, 200, f, headers)

        return HttpResponse(self.wfile, 404, io.BytesIO(b'not found'), {'Content-Type': 'text/html'})


class HttpResponse(object):
    def __init__(self, wfile, code=400, body=None, headers=None):
        self.wfile = wfile
        self.code = code
        self.body = io.BytesIO() if body is None else body
        self.headers = {} if headers is None else headers

    def flush(self):
        template = "HTTP/1.1 {}\nConnection: close\n{}\n\n"
        headers = '\n'.join('{}: {}'.format(k, self.headers[k]) for k in self.headers)
        enc = sys.getfilesystemencoding()
        head = template.format(self.code, headers, self.body).encode(enc, 'surrogateescape')
        self.wfile.write(head)
        shutil.copyfileobj(self.body, self.wfile)
        self.body.close()
        self.wfile.write(b'\n')
        self.wfile.flush()


def _get_args():
    parser = argparse.ArgumentParser(description='Simple HTTP server')
    parser.add_argument('PORT', default=8000, type=int, nargs='?', help='listening port')
    return parser.parse_args()


if __name__ == '__main__':
    args = _get_args()

    server = Server(args.PORT, RequestHandler)
    server.run_forever()
