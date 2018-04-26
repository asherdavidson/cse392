import socket
import threading
import socketserver
import sys

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

# FUSE(client) CODE
class Difuse():
    pass

# Server
class ServerHandler(socketserver.BaseRequestHandler):
    def handle(self):
        pass

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

if __name__ == "__main__":
    HOST, PORT = "localhost", 8000

    bt_addr = sys.argv[1]
    fuse_mnt_point = sys.argv[2]

    server = ThreadedTCPServer((HOST, PORT), ServerHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    # server_thread.daemon = True
    server_thread.start()
    print("Node server started on port: {}".format(PORT))
