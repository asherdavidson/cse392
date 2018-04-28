import os
import socket
import threading
import socketserver
import sys
import argparse
from stat import S_IFDIR, S_IFLNK, S_IFREG

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

from utils.message import Message
from utils.node import Node
from utils.handler import RequestHandler


class FuseApi(object):
    def __init__(self, bootstrap_node, local_node, local_files):
        self.bootstrap_node = bootstrap_node
        self.local_node     = local_node
        self.local_files    = local_files

        self.join_cluster()

    def __send_message(self, node, json):
        '''Sends a dict encoded into a json string to the given node
           (can send to the bootstrap node or any other node)'''
        json['port'] = self.local_node.port

        with socket.socket() as s:
            s.connect(node)

            s.sendall(Message.build(json))

            resp_len = s.recv(4)
            resp_data = s.recv(Message.parse_length(resp_len))

            return Message.parse(resp_len + resp_data)

    def join_cluster(self):
        '''Connects to the bootstrap node and attempts to JOIN the network'''
        resp = self.__send_message(self.bootstrap_node, {
            "command": "JOIN",
        })

        if resp['reply'] != 'ACK_JOIN':
            raise Exception('Could not join the network')

        resp = self.__send_message(self.bootstrap_node, {
            "command": "FILES_ADD",
            "files":   os.listdir(self.local_files),
        })

        if resp['reply'] != 'ACK_ADD':
            raise Exception('Could not add files to the network')

    def get_file_location(self, path):
        resp = self.__send_message(self.bootstrap_node, {
            'command': 'GET_FILE_LOC',
            'file': path,
        })

        if resp['reply'] == 'FILE_NOT_FOUND':
            raise FileNotFoundError()

        if resp['reply'] != 'ACK_GET_FILE_LOC':
            raise Exception('Could not lookup file location')

        return Node(resp['addr'], resp['port'])

    def getattr(self, path):
        if path == '/':
            stat = os.lstat(self.local_files)
            return dict((key, getattr(stat, key)) for key in
                        ('st_atime', 'st_ctime', 'st_gid', 'st_mode',
                         'st_mtime', 'st_nlink', 'st_size', 'st_uid'))

        node = self.get_file_location(path)

        if node == None:
            return None

        resp = self.__send_message(node, {
            'command': 'GET_ATTR',
            'path':    path,
        })

        if resp['reply'] != 'ACK_GET_ATTR':
            return None

        return resp['stat']

    def readdir(self):
        '''Gets the current directory contents from the bootstrap node'''
        resp = self.__send_message(self.bootstrap_node, {
            'command': 'LIST_DIR'
        })
        if resp['reply'] != 'ACK_LS':
            raise Exception('Could not read directory from bootstrap')

        return resp['files']


# FUSE(client) CODE
class DifuseFilesystem(Operations):
    def __init__(self, api):
        self.api = api

    def create(self, path, mode):
        print('create')
        # TODO
        pass

    def getattr(self, path, fh=None):
        print('getattr', path, fh)
        return self.api.getattr(path)

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
        return ['.'] + self.api.readdir()

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

class ServerHandler(RequestHandler):
    def process_msg(self, msg, client_node):
        cmd = msg.get('command')

        if cmd == 'GET_ATTR':
            path = os.path.join(api.local_files, msg['path'][1:])

            stat = os.lstat(path)
            stat = dict((key, getattr(stat, key)) for key in
                        ('st_atime', 'st_ctime', 'st_gid', 'st_mode',
                         'st_mtime', 'st_nlink', 'st_size', 'st_uid'))

            return {
                'reply': 'ACK_GET_ATTR',
                'stat': stat,
            }


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    pass


if __name__ == "__main__":
    global api

    parse = argparse.ArgumentParser()
    parse.add_argument("bootstrap_addr", type=str, help="Boot strap node address")
    parse.add_argument("bootstrap_port", type=int, help="Boot strap node port")
    parse.add_argument("mount_point",    type=str, help="FUSE mount point")
    parse.add_argument("local_files",    type=str, help="FUSE local file cache")
    parse.add_argument("-p", "--port",   type=int, default=8080, help="Server port (default 8080)")
    args = parse.parse_args()

    local_node = Node('localhost', args.port)
    bootstrap_node = Node(args.bootstrap_addr, args.bootstrap_port)
    fuse_mount_point = args.mount_point
    local_files  = args.local_files

    try:
        # Handle local_files dir
        if not os.path.exists(local_files):
            os.mkdir(local_files)

        if not os.path.isdir(local_files):
            raise ValueError('local_files exists, but is not a directory')

        # Handle mount point
        if not os.path.exists(fuse_mount_point):
            os.mkdir(fuse_mount_point)

        if not os.path.isdir(fuse_mount_point):
            raise ValueError('fuse_mount_point exists, but is not a directory')

        # Connect to Bootstrap node first. Exit on failure
        api = FuseApi(bootstrap_node, local_node, local_files)
        print("Registered with Bootstrap")
        print(f"We are {local_node.addr}:{local_node.port}")

        server = ThreadedTCPServer(local_node, ServerHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        print(f"Node server started on port: {local_node.port}")

        # start FUSE
        print(f"Fuse serving files at: {fuse_mount_point}")
        fuse = FUSE(DifuseFilesystem(api), fuse_mount_point, foreground=True)

    except Exception as e:
        raise e
