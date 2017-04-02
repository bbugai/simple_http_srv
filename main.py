import socket
import argparse
import os
import re
import mimetypes
from urllib.request import url2pathname


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
            response = self.request_handler.handle(request)
            client_connection.sendall(response.dump())
            client_connection.close()


class RequestHandler(object):
    @staticmethod
    def handle(request):
        index = RequestHandler._index()
        if index:
            return HttpResponse(200, index, )
        else:
            matches = re.findall('^GET(.*)HTTP', request.decode())
            if matches:
                return RequestHandler._serve_path(matches[0])

            return HttpResponse(body='bad request', headers={'Content-Type': 'text/html'})

    @staticmethod
    def _serve_path(url):
        url_path = url2pathname(url).strip()
        path = os.path.dirname(os.path.realpath(__file__)) + url_path
        if os.path.exists(path):
            if os.path.isdir(path):
                if not path.endswith('/'):
                    return HttpResponse(301, None, {'Location': url_path + '/'})

                files = ''.join('<li><a href="{0}">{0}</a>'.format(p) for p in os.listdir(path))
                headers = {'Content-Type': 'text/html'}
                return HttpResponse(200, '<h2>{}</h2><hr><ul>{}</ul><hr>'.format(path, files), headers)

            content_type, _ = mimetypes.guess_type(path)
            content_type = content_type if content_type else 'application/octet-stream'
            with open(path) as f:
                body = ''.join(line for line in f)

            return HttpResponse(200, body, {'Content-Type': content_type})

        return HttpResponse(404, 'not found', {'Content-Type': 'text/html'})

    @staticmethod
    def _index():
        index_path = os.path.join(os.getcwd(), 'index.html')

        if os.path.isfile(index_path):
            with open(index_path) as f:
                body = ''.join(line for line in f)

            return body

        return None


class HttpResponse(object):
    def __init__(self, code=400, body=None, headers=None):
        self.code = code
        self.body = '' if body is None else body
        self.headers = {} if headers is None else headers

    def dump(self):
        template = "HTTP/1.1 {}\nConnection: close\n{}\n\n{}\n"
        headers = '\n'.join('{}: {}'.format(k, self.headers[k]) for k in self.headers)
        return template.format(self.code, headers, self.body).encode()


def _get_args():
    parser = argparse.ArgumentParser(description='Simple HTTP server')
    parser.add_argument('PORT', default=8000, type=int, nargs='?', help='listening port')
    return parser.parse_args()


if __name__ == '__main__':
    args = _get_args()

    server = Server(args.PORT, RequestHandler)
    server.run_forever()
