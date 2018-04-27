import socket
import socketserver
import threading

import hashlib
import json
from construct import VarInt, PascalString

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

        for elem in self.client_list:
            if hash < elem[0]:
                return elem[1]
            
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
        # stores node ip to status? HW doc says we need it but idk
        self.nodes = set()
        # stores file name to ip addr
        self.file_dict = {}

    def add_file(self, file_name, addr):
        # TODO deal with duplicates?
        self.file_dict[file_name] = addr

    def remove_file(self, file_name):
        if file_name in self.file_dict:
            del self.file_dict[file_name]

    def get_file_location(self, file_name):
        return self.file_dict.get(file_name, "NOT FOUND")

    def add_node(self, addr):
        self.nodes.add(addr)

base_mgr = BaseProtocolManager()


# TODO move to shared file?
class Message():
    @classmethod
    def build(cld, obj):
        return PascalString(VarInt, "utf8").build(json.dumps(obj))

    @classmethod
    def parse(cls, msg):
        json_str = PascalString(VarInt, "utf8").parse(msg)
        return json.loads(json_str)


def process_msg(msg, request):
    cmd = msg.get('command')
    response = {}

    if cmd == 'JOIN':
        response['reply'] = 'ACK JOIN'
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
        data = self.request.recv(1024)
        # curr_thread = threading.current_thread()

        msg = Message.parse(data)
        process_msg(msg, self.request)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


if __name__ == "__main__":
    # TODO read host and port from config file/command line
    HOST, PORT = "localhost", 8000

    server = ThreadedTCPServer((HOST, PORT), BootstrapHandler)
    # ip, port = server.server_address

    server_thread = threading.Thread(target=server.serve_forever)
    # server_thread.daemon = True
    server_thread.start()

    print("Bootstrap server started on port: {}".format(PORT))
