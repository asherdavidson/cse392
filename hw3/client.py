import socket
import threading
import socketserver
import sys

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

# FUSE(client) CODE
class Difuse(Operations):
    
    def chmod(self, path, mod):
        print('chmod')
        pass

    def chown(self, path, uid, gid):
        print('chown')
        pass

    def getattr(self, path, fh=None):
        print('getattr')
        pass

    def getxattr(self, path, name, position=0):
        print('getxattr')
        pass

    def open(self, path, flags):
        print('open')
        pass

    def read(self, path, size, offset, fh):
        print('read')
        pass

    def write(self, path, data, offset, fh):
        print('write')
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

    # start FUSE
    # fuse = FUSE(Difuse(), fuse_mnt_point, foreground=True)

    server = ThreadedTCPServer((HOST, PORT), ServerHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    # server_thread.daemon = True
    server_thread.start()
    print("Node server started on port: {}".format(PORT))
