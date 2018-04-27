import socket
import threading
import socketserver
import sys

import argparse
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
    parse = argparse.ArgumentParser()
    parse.add_argument("bt_addr",   type=str,   help="Boot strap node address")
    parse.add_argument("bt_port",   type=int,   help="Boot strap node port")
    parse.add_argument("mnt_point", type=str,   help="FUSE mount point")
    parse.add_argument("--port",    type=int,   default=8080, help="Server port (default 8080)")
    args = parse.parse_args()

    HOST, PORT      = "localhost", args.port

    bt_addr         = args.bt_addr
    bt_port         = args.bt_port
    fuse_mnt_point  = args.mnt_point

    # start FUSE
    # fuse = FUSE(Difuse(), fuse_mnt_point, foreground=True)

    server = ThreadedTCPServer((HOST, PORT), ServerHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    # server_thread.daemon = True
    server_thread.start()
    print("Node server started on port: {}".format(PORT))
