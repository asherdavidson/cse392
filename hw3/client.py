import os
import socket
import threading
import socketserver
import sys
import argparse
from stat import S_IFDIR, S_IFLNK, S_IFREG

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

from utils.message import Message


def send_message(addr, port, json):
    with socket.socket() as s:
        s.connect((addr, port))

        s.sendall(Message.build(json))

        resp_len = s.recv(4)
        resp_data = s.recv(Message.parse_length(resp_len))

        return Message.parse(resp_len + resp_data)


# FUSE(client) CODE
class DifuseFilesystem(Operations):
    def __init__(self, file_cache):
        self.file_cache = file_cache

    def create(self, path, mode):
        print('create')
        # TODO
        pass

    def getattr(self, path, fh=None):
        print('getattr', path, fh)
        # TODO

        stat = os.lstat(os.path.join(self.file_cache, path[1:]))
        return dict((key, getattr(stat, key)) for key in ('st_atime', 'st_ctime',
                    'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))

    def open(self, path, flags):
        print('open')
        # TODO
        pass

    def read(self, path, size, offset, fh):
        print('read')
        # TODO
        pass

    def readdir(self, path, fh):
        print('readdir')
        # TODO
        return ['.'] + os.listdir(self.file_cache)

    def rename(self, old, new):
        print('rename')
        # TODO
        pass

    def statfs(self, path):
        print('statfs')
        pass

    def truncate(self, path, length, fh=None):
        print('truncate')
        pass

    def utimens(self, path, times=None):
        print('utimens')
        pass

    def write(self, path, data, offset, fh):
        print('write')
        # TODO
        pass


# Server
class ServerHandler(socketserver.BaseRequestHandler):
    def handle(self):
        pass


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    pass

def join_cluster(bt_addr, bt_port, node_port, local_files):
    '''
        Takes bootstrap node addr and port, node_port, and files_list
    '''
    resp = send_message(bt_addr, bt_port, {
        "command"   :   "JOIN",
        "port"      :   node_port
    })
    
    if resp['reply'] != 'ACK_JOIN': return False

    resp = send_message(bt_addr, bt_port, {
        "command"   :   "FILES_ADD",
        "files"     :   local_files,
        "port"      :   node_port
    })

    return resp['reply'] == 'ACK_ADD'


if __name__ == "__main__":
    parse = argparse.ArgumentParser()
    parse.add_argument("bootstrap_addr", type=str, help="Boot strap node address")
    parse.add_argument("bootstrap_port", type=int, help="Boot strap node port")
    parse.add_argument("mount_point",    type=str, help="FUSE mount point")
    parse.add_argument("file_cache",     type=str, help="FUSE local file cache")
    parse.add_argument("--port",         type=int, default=8080, help="Server port (default 8080)")
    args = parse.parse_args()

    HOST, PORT = "localhost", args.port

    bootstrap_addr   = args.bootstrap_addr
    bootstrap_port   = args.bootstrap_port
    fuse_mount_point = args.mount_point
    file_cache  = args.file_cache

    # Handle file_cache dir
    if not os.path.exists(file_cache):
        os.mkdir(file_cache)

    if not os.path.isdir(file_cache):
        raise ValueError('file_cache exists, but is not a directory')

    # Connect to Bootstrap node first. Exit on failure
    local_files = os.listdir(file_cache)

    if not join_cluster(bootstrap_addr, bootstrap_port, PORT, local_files):
        sys.exit()
    print("Registered with Bootstrap")

    server = ThreadedTCPServer((HOST, PORT), ServerHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    print("Node server started on port: {}".format(PORT))

    # start FUSE
    print("Fuse serving files at: {}".format(fuse_mount_point))
    fuse = FUSE(DifuseFilesystem(file_cache), fuse_mount_point, foreground=True)
