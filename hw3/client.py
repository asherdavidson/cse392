import os
import socket
import threading
import socketserver
import sys
import argparse
from time import time
from stat import S_IFDIR, S_IFLNK, S_IFREG
from errno import *
from base64 import b64decode, b64encode

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

from utils.message import Message
from utils.node import Node
from utils.handler import RequestHandler


class FuseApi(object):
    def __init__(self, bootstrap_node, local_node, local_files):
        self.bootstrap_node = bootstrap_node
        self.local_node     = local_node
        self.local_files    = local_files

        # consistent hash id
        self.id = None

        self.join_cluster()

    def __send_message(self, node, json):
        '''Sends a dict encoded into a json string to the given node
           (can send to the bootstrap node or any other node)'''
        json['port'] = self.local_node.port

        with socket.socket() as s:
            try:
                s.connect(node)
            except Exception as e:
                self.report_missing_node(node)
                raise e

            s.sendall(Message.build(json))

            resp_len = s.recv(4)
            resp_data = s.recv(Message.parse_length(resp_len))

            return Message.parse(resp_len + resp_data)

    def __send_file(self, node, path):
        '''
            sends file and deletes local copy after receiving confirmation
        '''
        local_path = os.path.join(self.local_files, path[1:])
        with open(local_path, 'rb') as f:
            buf = f.read()

        msg = {
            'command': 'SEND_FILE',
            'file_name': path[1:],
            'data': b64encode(buf).decode(),
        }

        resp = self.__send_message(node, msg)

        if resp['reply'] == 'ACK_WRITE':
            os.unlink(local_path)
        else:
            # raise error
            pass

    def join_cluster(self):
        '''Connects to the bootstrap node and attempts to JOIN the network'''
        resp = self.__send_message(self.bootstrap_node, {
            "command": "JOIN",
        })

        if resp['reply'] != 'ACK_JOIN':
            raise Exception('Could not join the network')

        self.local_node = Node(resp['local_addr'], resp['local_port'])
        self.id = resp['id']

        # need to receive files from next node in consistent hash cluster
        # if resp['next_addr'] != 'NONE':
        #     resp = self.__send_message(Node(resp['next_addr'], resp['next_port']), {

        #     })

        # need to computer hash for files and send to other nodes
        resp = self.__send_message(self.bootstrap_node, {
            "command": "FILES_ADD",
            "files":   os.listdir(self.local_files),
        })

        if resp['reply'] != 'ACK_ADD':
            raise Exception('Could not add files to the network')

    def shutdown(self):
        resp = self.__send_message(self.bootstrap_node, {
            'command': 'LEAVE',
        })

    def report_missing_node(self, node):
        resp = self.__send_message(self.bootstrap_node, {
            'command': 'MISSING_NODE',
            'maddr': node.addr,
            'mport': node.port,
        })

    def get_file_location(self, path):
        resp = self.__send_message(self.bootstrap_node, {
            'command': 'GET_FILE_LOC',
            'file': path,
        })

        if resp['reply'] == 'FILE_NOT_FOUND':
            raise FuseOSError(ENOENT)

        if resp['reply'] != 'ACK_GET_FILE_LOC':
            raise FuseOSError(ENOENT)

        return Node(resp['addr'], resp['port'])

    def create(self, path, mode):
        # check if file exists in cluster before creating
        # get_file_location errors out if this fails
        try:
            resp = self.get_file_location(path)
            if resp:
                return 0
        except Exception:
            pass

        local_path = os.path.join(self.local_files, path[1:])
        f = open(local_path, 'x')
        f.close()
        os.chmod(local_path, mode)

        resp = self.__send_message(self.bootstrap_node, {
            'command': 'FILE_ADD',
            'path': path,
        })

        return 0

    def getattr(self, path):
        node = self.get_file_location(path)

        resp = self.__send_message(node, {
            'command': 'GET_ATTR',
            'path':    path,
        })

        if resp['reply'] != 'ACK_GET_ATTR':
            raise FuseOSError(ENOENT)

        return resp['stat']

    def read(self, path, size, offset, fh):
        node = self.get_file_location(path)

        # read locally
        if node == self.local_node:
            localpath = os.path.join(self.local_files, path[1:])

            with open(localpath, 'rb') as f:
                f.seek(offset)
                return f.read(size)

        # read from network
        else:
            resp = self.__send_message(node, {
                'command': 'READ',
                'path': path,
                'size': size,
                'offset': offset,
            })

            if resp['reply'] != 'ACK_READ':
                raise FuseOSError(EIO)

            return b64decode(resp['data'].encode())

    def write(self, path, data, offset, fh):
        node = self.get_file_location(path)

        if node == self.local_node:
            localpath = os.path.join(self.local_files, path[1:])

            with open(localpath, 'wb') as f:
                f.seek(offset)
                return f.write(data)

        else:
            resp = self.__send_message(node, {
                'command': 'WRITE',
                'path': path,
                'offset': offset,
                'data': b64encode(data).decode()
            })

            if resp['reply'] != 'ACK_WRITE':
                raise FuseOSError(EIO)

            return len(data)

    def readdir(self):
        '''Gets the current directory contents from the bootstrap node'''
        resp = self.__send_message(self.bootstrap_node, {
            'command': 'LIST_DIR'
        })
        if resp['reply'] != 'ACK_LS':
            raise FuseOSError(ENOENT)

        # print('Files: {}'.format(resp["files"]))
        return resp['files']

    def truncate(self, path, length, fh):
        node = self.get_file_location(path)

        if node == self.local_node:
            localpath = os.path.join(self.local_files, path[1:])
            os.truncate(localpath, length)

        else:
            resp = self.__send_message(node, {
                'command': 'TRUNCATE',
                'path': path,
                'length': length,
            })

            if resp['reply'] != 'ACK_TRUNCATE':
                raise FuseOSError(EIO)

    def utimens(self, path, times):
        node = self.get_file_location(path)

        if node == self.local_node:
            localpath = os.path.join(self.local_files, path[1:])
            os.utime(localpath, times=times)

        else:
            resp = self.__send_message(node, {
                'command': 'UTIMENS',
                'path': path,
                'times': times,
            })

            if resp['reply'] != 'ACK_UTIMENS':
                raise FuseOSError(EIO)

        return 0

    def unlink(self, path):
        # We need to delete from bootstrap and node
        node = self.get_file_location(path)

        if node == self.local_node:
            localpath = os.path.join(self.local_files, path[1:])
            os.unlink(localpath)

        else:
            resp = self.__send_message(node, {
                'command': 'UNLINK',
                'path': path,
            })

            if resp['reply'] != 'ACK_UNLINK':
                raise FuseOSError(EIO)

        # could make it into single bootstrap call
        resp = self.__send_message(self.bootstrap_node, {
            'command': 'FILE_REMOVE',
            'path': path,
        })

        if resp['reply'] != 'ACK_RM':
            raise FuseOSError(EIO)


# FUSE(client) CODE
class DifuseFilesystem(Operations):
    def __init__(self, api):
        self.api = api

        now = time()
        self.root = dict(st_mode=(S_IFDIR | 0o755), st_ctime=now,
                         st_mtime=now, st_atime=now, st_nlink=2)

    def create(self, path, mode):
        print('create', path, mode)
        return self.api.create(path, mode)

    def getattr(self, path, fh=None):
        print('getattr', path, fh)
        if path == '/':
            return self.root

        return self.api.getattr(path)

    def open(self, path, flags):
        print('open', path, flags)
        # We don't need to actually open the file,
        # we can just return 0 and handle read
        return self.api.create(path, 0o755)
        # return 0

    def read(self, path, size, offset, fh):
        print('read', path, size, offset, fh)
        return self.api.read(path, size, offset, fh)

    def readdir(self, path, fh):
        print(f'readdir {path}')
        return self.api.readdir()

    statfs = None
    # def statfs(self, path):
    #     print(f'statfs {path}')
    #     pass

    def truncate(self, path, length, fh=None):
        print(f'truncate {path} to {length}')
        return self.api.truncate(path, length, fh)

    def utimens(self, path, times=None):
        print('utimens', path, times)
        self.api.utimens(path, times)
        pass

    def write(self, path, data, offset, fh):
        print('write', path, len(data), offset)
        return self.api.write(path, data, offset, fh)

    def unlink(self, path):
        print(f'unlink {path}')
        return self.api.unlink(path)

    def destroy(self, path):
        print('destroy')
        shutdown()


# Server
class ServerHandler(RequestHandler):
    def process_msg(self, msg, client_node):
        cmd = msg.get('command')

        if cmd == 'GET_ATTR':
            return self.get_attr(msg)

        elif cmd == 'READ':
            return self.read(msg)

        elif cmd == 'WRITE':
            return self.write(msg)

        elif cmd == 'SEND_FILE':
            return self.write(msg, True)

        elif cmd == 'TRUNCATE':
            return self.truncate(msg)

        elif cmd == 'UTIMENS':
            return self.utimens(msg)

        elif cmd == 'UNLINK':
            return self.unlink(msg)

        elif cmd == 'PING':
            return self.ping(msg)

    def utimens(self, msg):
        path = os.path.join(api.local_files, msg['path'][1:])
        times = msg['times']

        os.utime(path, times=tuple(times))

        return {
            'reply': 'ACK_UTIMENS',
        }

    def read(self, msg):
        path = os.path.join(api.local_files, msg['path'][1:])
        size = msg['size']
        offset = msg['offset']

        with open(path, 'rb') as f:
            f.seek(offset)
            buf = f.read(size)

        return {
            'reply': 'ACK_READ',
            'data': b64encode(buf).decode(),
        }

    def write(self, msg, create=False):
        path = os.path.join(api.local_files, msg['path'][1:])
        data = b64decode(msg['data'].encode())

        with open(path, 'wb') as f:
            if not create:
                offset = msg['offset']
                f.seek(offset)
            f.write(data)

        return {
            'reply': 'ACK_WRITE',
        }

    def truncate(self, msg):
        path = os.path.join(api.local_files, msg['path'][1:])
        length = msg['length']

        os.truncate(path, length)

        return {
            'reply': 'ACK_TRUNCATE',
        }

    def get_attr(self, msg):
        path = os.path.join(api.local_files, msg['path'][1:])

        stat = os.lstat(path)
        stat = dict((key, getattr(stat, key)) for key in
                    ('st_atime', 'st_ctime', 'st_gid', 'st_mode',
                     'st_mtime', 'st_nlink', 'st_size', 'st_uid'))

        return {
            'reply': 'ACK_GET_ATTR',
            'stat': stat,
        }

    def unlink(self, msg):
        path = os.path.join(api.local_files, msg['path'][1:])

        os.unlink(path)

        return {
            'reply': 'ACK_UNLINK'
        }

    def ping(self, msg):
        return {
            'reply': 'ACK_PING'
        }


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    pass


def shutdown():
    # api.shutdown()
    server.shutdown()


if __name__ == "__main__":
    global api
    global server

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
        print(f"We are {api.local_node.addr}:{api.local_node.port}")

        # Start the local server
        server = ThreadedTCPServer(api.local_node, ServerHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        print(f"Node server started on port: {api.local_node.port}")

        # start FUSE
        print(f"Fuse serving files at: {fuse_mount_point}")
        fuse = FUSE(DifuseFilesystem(api), fuse_mount_point, foreground=True)

    except SystemExit:
        print('ctrl-c')
        # api.disconnect()

    except Exception as e:
        raise e
