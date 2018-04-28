import socketserver

from utils.message import Message
from utils.node import Node

class RequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        length = self.request.recv(4)
        data = self.request.recv(Message.parse_length(length))

        msg = Message.parse(length + data)

        host = self.client_address[0]
        port = msg.get('port')
        client_node = Node(host, port)

        response = self.process_msg(msg, client_node)
        if response:
            self.request.sendall(Message.build(response))

    def process_msg(self, msg, client_node):
        pass
