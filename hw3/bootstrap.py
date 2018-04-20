import socket
import socketserver
import threading

class ThreadedBootstrapHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = bytes(self.request.recv(1024), 'ascii')
        curr_thread = threading.current_thread()

        # TODO: parse json and length field

        # TODO: process request

        response = bytes("Hello!", "ascii")
        self.request.sendall(response)

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

if __name__ == "__main__":
    # TODO read host and port from config file/command line
    HOST = "localhost"
    PORT = 8000

    server = ThreadedTCPServer((HOST, PORT), ThreadedBootstrapHandler)
    ip, port = server.server_address

    server_thread = threading.Thread(target=server.serve_forever)
    # server_thread.daemon = True
    server_thread.start()

    print("Started server on port {}".format(port))
