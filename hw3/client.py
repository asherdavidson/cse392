import os
import socket
import threading
import socketserver
import sys
import argparse
from time import time
from stat import S_IFDIR, S_IFLNK, S_IFREG

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

from utils.message import Message


global PORT
global bootstrap_addr
global bootstrap_port
global file_cache


def send_message(addr, port, json):
    global PORT

    json['port'] = PORT

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

        now             = time()
        self.root       = dict(st_mode=(S_IFDIR | 0o755), st_ctime=now,
                                st_mtime=now, st_atime=now, st_nlink=1)

    def create(self, path, mode):
        print('create')
        # TODO
        pass

    def getattr(self, path, fh=None):
        print('getattr', path, fh)

        if path == '/': return self.root

        path = path[1:]
        resp = send_message(bootstrap_addr, bootstrap_port, {
            'command'   : 'GET_ATTR',
            'path'      : path
        })

        if resp['reply'] != 'ACK_LOOKUP':   return None

        target_addr = resp['target_addr']
        target_port = resp['target_port']

        print(f'target {target_addr} {type(target_port)}')

        resp = send_message(target_addr, target_port, {
            'command'   : 'GET_ATTR',
            'path'      : path
        })

        return resp['attr']

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

        resp = send_message(bootstrap_addr, bootstrap_port, {
            'command'   : 'LIST_DIR'
        })

        return resp['files']
        # return ['.'] + os.listdir(self.file_cache)

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
def process_msg(msg, request, client_addr):
    cmd = msg.get('command')
    response = {}

    if cmd == 'GET_ATTR':
        path = msg.get('path')
        stat = os.lstat(os.path.join(file_cache, path))
        response['attr'] = dict((key, getattr(stat, key)) for key in ('st_atime', 'st_ctime',
                    'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))

    request.sendall(Message.build(response))


# TODO move server handler to a separate file since it's the same as bootstrap
class ServerHandler(socketserver.BaseRequestHandler):
    def handle(self):
        length = self.request.recv(4)
        data = self.request.recv(Message.parse_length(length))

        msg = Message.parse(length + data)
        process_msg(msg, self.request, self.client_address)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    pass


def join_cluster(bt_addr, bt_port, local_files):
    '''
        Takes bootstrap node addr and port, node_port, and files_list
    '''
    resp = send_message(bt_addr, bt_port, {
        "command"   : "JOIN",
    })

    if resp['reply'] != 'ACK_JOIN':
        return False

    resp = send_message(bt_addr, bt_port, {
        "command"   : "FILES_ADD",
        "files"     : local_files,
    })

    return resp['reply'] == 'ACK_ADD'


if __name__ == "__main__":
    global PORT
    global bootstrap_addr
    global bootstrap_port
    global file_cache

    parse = argparse.ArgumentParser()
    parse.add_argument("bootstrap_addr", type=str, help="Boot strap node address")
    parse.add_argument("bootstrap_port", type=int, help="Boot strap node port")
    parse.add_argument("mount_point",    type=str, help="FUSE mount point")
    parse.add_argument("file_cache",     type=str, help="FUSE local file cache")
    parse.add_argument("--port",         type=int, default=8080, help="Server port (default 8080)")
    args = parse.parse_args()

    HOST, PORT          = "localhost", args.port

    bootstrap_addr      = args.bootstrap_addr
    bootstrap_port      = args.bootstrap_port
    fuse_mount_point    = args.mount_point
    file_cache          = args.file_cache

    # Handle file_cache dir
    if not os.path.exists(file_cache):
        os.mkdir(file_cache)

    if not os.path.isdir(file_cache):
        raise ValueError('file_cache exists, but is not a directory')

    # Connect to Bootstrap node first. Exit on failure
    local_files = [file for file in os.listdir(file_cache)
                    if os.path.isfile(os.path.join(file_cache, file))]
    # os.listdir(file_cache)
    print(local_files)

    if not join_cluster(bootstrap_addr, bootstrap_port, local_files):
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
