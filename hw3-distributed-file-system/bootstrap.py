import socket
import socketserver
import threading
import argparse
import hashlib

from utils.message import Message
from utils.node import Node
from utils.handler import RequestHandler

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

    def add_file(self, file_name, node):
        if file_name in self.file_dict:
            return False
        self.file_dict[file_name] = node
        return True

    def remove_file(self, file_name):
        if file_name in self.file_dict:
            del self.file_dict[file_name]

    def get_files_list(self):
        return list(self.file_dict.keys()) + ['.', '..']

    def get_file_location(self, file_name):
        return self.file_dict.get(file_name[1:], None)

    def add_client(self, node):
        if node in self.nodes:
            return False
        else:
            self.nodes.add(node)
            return True

    def remove_client(self, node):
        if node in self.nodes:
            self.nodes.remove(node)

            node_files = [file for file, fnode in self.file_dict.items() if fnode == node]
            for file in node_files:
                self.remove_file(file)


base_mgr = BaseProtocolManager()


class BootstrapHandler(RequestHandler):
    def __send_message(self, node, json):
        global PORT

        json['port'] = PORT

        with socket.socket() as s:
            s.connect(node)
            s.sendall(Message.build(json))

            resp_len = s.recv(4)
            resp_data = s.recv(Message.parse_length(resp_len))

            return Message.parse(resp_len + resp_data)

    def process_msg(self, msg, client_node):
        cmd = msg.get('command')

        if cmd == 'JOIN':
            return self.join(client_node)

        elif cmd == 'FILES_ADD':
            return self.add_files(msg, client_node)

        elif cmd == 'FILE_ADD':
            return self.add_file(msg, client_node)

        elif cmd == 'FILE_REMOVE':
            return self.remove_file(msg, client_node)

        elif cmd == 'GET_FILE_LOC':
            return self.get_file_loc(msg)

        elif cmd == 'LIST_DIR':
            return self.list_dir()

        elif cmd == 'LEAVE':
            return self.leave(client_node)

        elif cmd == 'MISSING_NODE':
            return self.missing_node(msg)

        else:
            print(f'Unknown command: {cmd}')

    def join(self, client_node):
        if base_mgr.add_client(client_node):
            print(f'{client_node} joined')
            return {
                'reply': 'ACK_JOIN',
                'local_addr': client_node.addr,
                'local_port': client_node.port,
            }

        else:
            print(f'{client_node} failed to join')
            return {
                'reply': 'JOIN_FAILED',
            }

    def add_files(self, msg, client_node):
        files_list = msg.get('files')

        # shouldn't expect any problems for now
        if files_list:
            for f in files_list:
                base_mgr.add_file(f, client_node)

        print(f'{client_node} added {len(files_list)} files')
        return {
            'reply': 'ACK_ADD',
        }

    def add_file(self, msg, client_node):
        filename = msg['path'][1:]
        if base_mgr.add_file(filename, client_node):
            print(f'{client_node} added {filename}')
            return {
                'reply': 'ACK_ADD',
            }
        else:
            return {
                'reply': 'FILE_ALREADY_EXISTS'
            }

    def remove_file(self, msg, client_node):
        filename = msg['path'][1:]
        base_mgr.remove_file(filename)
        print(f'{client_node} removed {filename}')

        return {
            'reply': 'ACK_RM',
        }

    def get_file_loc(self, msg):
        node = base_mgr.get_file_location(msg['file'])
        if node == None:
            return {
                'reply': 'FILE_NOT_FOUND'
            }

        return {
            'reply': 'ACK_GET_FILE_LOC',
            'addr': node.addr,
            'port': node.port,
        }

    def list_dir(self):
        return {
            'reply': 'ACK_LS',
            'files': base_mgr.get_files_list(),
        }

    def leave(self, client_node):
        base_mgr.remove_client(client_node)
        print(f'{client_node} left')
        return {
            'reply': 'ACK_LEAVE',
        }

    def missing_node(self, msg):
        node = Node(msg['maddr'], msg['mport'])

        try:
            self.__send_message(node, {
                'command': 'PING',
            })

            return {
                'reply': 'NODE_ALIVE'
            }

        except:
            base_mgr.remove_client(node)
            print(f'{node} died')
            return {
                'reply': 'NODE_DEAD'
            }


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


if __name__ == "__main__":
    global HOST
    global PORT

    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--host', type=str, default='localhost', help='IP to serve from')
    parser.add_argument("-p", "--port", type=int, default=8000, help="Port number to listen on (default 8000)")
    args = parser.parse_args()

    HOST, PORT = args.host, args.port

    server = ThreadedTCPServer((HOST, PORT), BootstrapHandler)
    # ip, port = server.server_address

    server_thread = threading.Thread(target=server.serve_forever)
    # server_thread.daemon = True
    server_thread.start()

    print("Bootstrap server started on port: {}".format(PORT))

    # TODO: repl???
