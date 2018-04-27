import socket
import socketserver
import threading

import argparse
import hashlib

from utils.message import Message

class ConsistentHashManager():
    def __init__(self, range):
        # determines possible machine id's from [0-range)
        self.range = range

        # used to check if client already exists
        # self.client_id_set = set()

        # list elements will be in the form (id, addr)
        self.client_list = []

    def __len__(self):
        return len(self.client_list)

    def __str__(self):
        return str(self.client_list)

    def add_client(self, addr):
        '''
            hash client addr and add to list, return id
        '''
        # hash and find insertion position
        id = self.hash(addr)

        # linear search
        pos = 0
        # flag to append at end of list
        at_end = True
        for idx, elem in enumerate(self.client_list):
            if id < elem[0]:
                pos = idx
                at_end = False
                break

        if at_end:
            self.client_list.append((id, addr))
        else:
            self.client_list.insert(pos, (id, addr))

        return id


    def get_client(self, hash):
        '''
            find client that hash should go to
            returns addr
        '''
        if not self.client_list:
            return None

        for id, addr in self.client_list:
            if hash < id:
                return addr

        return self.client_list[0][1]


    def remove_client(self, id):
        '''
            remove client
            return True if success False otherwise
        '''
        pos = -1
        for idx, elem in enumerate(self.client_list):
            if elem[0] == id:
                pos = idx

        if pos == -1:
            return False

        self.client_list.pop(pos)
        return True


    def hash(self, key):
        hashobj = hashlib.sha224(bytes(key.encode()))
        hash = int.from_bytes(hashobj.digest(), 'big')
        return hash % self.range


# Ignore consistent hashing for now and implement base code
class BaseProtocolManager():
    def __init__(self):
        # stores (addr, port) tuple
        self.nodes = set()
        # stores file name to (addr, port) tuple
        self.file_dict = {}

    def add_file(self, file_name, addr, port):
        # TODO deal with duplicates?
        self.file_dict[file_name] = (addr, port)

    def remove_file(self, file_name):
        if file_name in self.file_dict:
            del self.file_dict[file_name]

    def get_file_location(self, file_name):
        return self.file_dict.get(file_name, "NOT FOUND")

    def add_client(self, addr, port):
        new_node = (addr, port)
        if new_node in self.nodes:
            return False
        else:
            self.nodes.add(new_node)
            return True

base_mgr = BaseProtocolManager()


def process_msg(msg, request, client_addr):
    cmd = msg.get('command')
    host = client_addr[0]
    response = {}

    if cmd == 'JOIN':
        port = msg.get('port')

        if base_mgr.add_client(host, port):
            response['reply'] = 'ACK_JOIN'
            print(f'{client_addr} joined')
        else:
            response['reply'] = 'JOIN_FAILED'
            print(f'{client_addr} failed to join')
    elif cmd == 'FILES_ADD':
        port = msg.get('port')

        files_list = msg.get('files')
        
        # shouldn't expect any problems for now
        for f in files_list:
            base_mgr.add_file(f, host, port)

        print(f'{client_addr} added {len(files_list)} files')
        response['reply'] = 'ACK_ADD'        
    elif cmd == 'FILE_ADD':
        response['reply'] = 'ACK ADD'

    elif cmd == 'FILE_REMOVE':
        response['reply'] = 'ACK RM'

    elif cmd == 'FILE_LOOKUP':
        response['reply'] = 'ACK LOOKUP'

    elif cmd == 'LIST_DIR':
        response['reply'] = 'ACK LS'

    elif cmd == 'LEAVE':
        response['reply'] = 'ACK LEAVE'

    request.sendall(Message.build(response))


class BootstrapHandler(socketserver.BaseRequestHandler):
    def handle(self):
        length = self.request.recv(4)
        data = self.request.recv(Message.parse_length(length))
        # curr_thread = threading.current_thread()

        msg = Message.parse(length + data)
        process_msg(msg, self.request, self.client_address)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000, help="Port number to listen on (default 8000)")
    args = parser.parse_args()

    HOST, PORT = "localhost", args.port

    server = ThreadedTCPServer((HOST, PORT), BootstrapHandler)
    # ip, port = server.server_address

    server_thread = threading.Thread(target=server.serve_forever)
    # server_thread.daemon = True
    server_thread.start()

    print("Bootstrap server started on port: {}".format(PORT))

    # TODO: repl???
