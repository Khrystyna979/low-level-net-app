from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import mimetypes
import pathlib
import socket
from datetime import datetime
import json
import logging
from threading import Thread
import os

HTTP_PORT = 3000
SOCKET_PORT = 5000
SOCKET_HOST = '127.0.0.1'
HTTP_HOST = '0.0.0.0'
BUFFER_SIZE = 1024
FILE_PATH = 'storage/data.json'

class HttpHandler(BaseHTTPRequestHandler):
    """
    Created own http server with post, get methods and method for static resourses
    """
    def do_GET(self):
        """Process an incoming HTTP GET request.

        Parses the request path via urllib and determines which page
        or resource to return to the user (routing).
        """
        pr_url = urllib.parse.urlparse(self.path) 
        match pr_url.path: 
            case '/':
                self.send_html_file('front-init/index.html')
            case '/message':
                self.send_html_file('front-init/message.html')
            case _:
                resource_path = pathlib.Path('front-init').joinpath(pr_url.path[1:])
                if resource_path.exists(): 
                    self.send_static()
                else:
                    self.send_html_file('front-init/error.html', 404)
                    
    def do_POST(self):
        """Process an incoming HTTP POST request.

        Read a specific amount of bytes from the form data. Send this data 
        to socket using the UDP protocol and redirect the user to index.html.
        """
        if self.path == '/message':
            data = self.rfile.read(int(self.headers['Content-Length'])) # rfile - Це вхідний потік даних від браузера до сервера
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket: 
                client_socket.sendto(data, (SOCKET_HOST, SOCKET_PORT)) 

            self.send_response(302) 
            self.send_header('Location', '/')
            self.end_headers()  
        else:
            self.send_error(404, 'Page not found')


    def send_html_file(self, filename: str, status: int=200):
        """Send HTML file to the browser.

        Args:
            filename (str): The path or location of the HTML file to be sent.
            status (int, optional): HTTP response status code. Defaults to 200.
        """
        self.send_response(status) 
        self.send_header('Content-type', 'text/html') 
        self.end_headers() 
        with open(filename, 'rb') as fd: 
            self.wfile.write(fd.read()) # wfile це спеціальний "канал зв'язку" між сервером і браузером користувача, вимагає байти тому rb
    def send_static(self):
        """Determine the file type and send a static resource to the client.

        Uses the request path to guess the MIME type. If the type cannot be 
        determined, defaults to 'text/plain'. Reads the file from the local 
        file system and writes its binary content to the output stream.
        """
        self.send_response(200)  
        mt = mimetypes.guess_type(self.path) 
        if mt:
            self.send_header("Content-type", mt[0])
        else:
            self.send_header("Content-type", 'text/plain') 
        self.end_headers() 
        file_path = pathlib.Path('front-init').joinpath(self.path[1:])
        with open(file_path, 'rb') as file: 
            self.wfile.write(file.read())
               
def save_data_from_form(data: bytes, file_path: str):
    """Format data into a dictionary and save it to a JSON file.
    
    Decodes the incoming bytes, parses them into a dictionary, and adds a 
    timestamp. If the file at 'file_path' exists, it loads existing data 
    before updating; otherwise, it creates a new storage file.

    Args:
        data (bytes): Raw data received from the socket.
        file_path (str): destination path for the JSON storage file.
    """  
    data_parse = urllib.parse.unquote_plus(data.decode()) # unquote_plus ця функція повертає у людський вигляд запис, але частини форми будуть розділені '&'
    try:
        data_dict = {key: value for key, value in [el.split('=', 1) for el in data_parse.split('&')]} 
        time = str(datetime.now())
        message = {time: data_dict} 
        print(message)
        with open(file_path, 'r', encoding='utf-8') as jsfile:
            try:
                final_data_dict = json.load(jsfile) 
            except json.JSONDecodeError: 
                    final_data_dict = {}
        final_data_dict.update(message) 
        with open(file_path, 'w', encoding='utf-8') as jsfile:
            json.dump(final_data_dict, jsfile, indent=4, ensure_ascii=False) 
    except ValueError as err: 
        logging.error(err)
    except OSError as err: 
        logging.error(err)
    
def run_socket_server(socket_host: str, socket_port: int):
    """Create and run a UDP socket server.

    Starts a persistent server that listens for incoming data on the specified 
    host and port. Received data is processed and saved via save_data_from_form.
    The server runs until a KeyboardInterrupt is received.

    Args:
        socket_host (str): The IP address or hostname to bind the socket to.
        socket_port (int): The port number to listen on.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((socket_host, socket_port))
    try:
        while True:
            data, address = sock.recvfrom(BUFFER_SIZE)
            print(f'Get message by {address}')
            save_data_from_form(data, FILE_PATH)
    except KeyboardInterrupt:
        print('Destroyed server')
    finally:
        sock.close()


def run_http_server(http_host: str, http_port: int):
    """Initialize and start the HTTP server.

    Creates an instance of HTTPServer bound to the specified host and port.
    The server listens for incoming HTTP requests and processes them using 
    the HttpHandler class. It runs indefinitely until manually interrupted.

    Args:
        http_host (str): The IP address or hostname to bind the HTTP server to.
        http_port (int): The port number for the HTTP server to listen on.
    """
    address = (http_host, http_port)
    http_server = HTTPServer(address, HttpHandler)
    logging.info("Starting http server")
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()


if __name__ == '__main__':
    if not os.path.exists('storage'):
        os.makedirs('storage')
    if not os.path.exists(FILE_PATH):
        with open(FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump({}, f)
    
    # Set logs for threads
    logging.basicConfig(level=logging.DEBUG, format='%(threadName)s %(message)s')
    # Create and run http server thread
    server = Thread(target=run_http_server, args=(HTTP_HOST, HTTP_PORT))
    server.start()
    # Create and run socket server thread
    server_socket = Thread(target=run_socket_server, args=(SOCKET_HOST, SOCKET_PORT))
    server_socket.start()
