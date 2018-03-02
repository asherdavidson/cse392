import socket
import argparse
import select
import sys

from queue import Queue
from threading import Thread
from enum import Enum, auto


CONNECT                              = "ME2U"
CONNECT_RESPONSE                     = "U2EM"
REGISTER_USERNAME                    = "IAM"
REGISTER_USERNAME_RESPONSE_TAKEN     = "ETAKEN"
REGISTER_USERNAME_RESPONSE_SUCCESS   = "MAI"
DAILY_MESSAGE                        = "MOTD"
LIST_USERS                           = "LISTU"
LIST_USERS_RESPONSE                  = "UTSIL"
SEND_MESSAGE                         = "TO"
SEND_MESSAGE_RESPONSE_SUCCESS        = "OT"
SEND_MESSAGE_RESPONSE_DOES_NOT_EXIST = "EDNE"
RECEIVE_MESSAGE                      = "FROM"
RECEIVE_MESSAGE_SUCCESS              = "MORF"
LOGOUT                               = "BYE"
LOGOUT_RESPONSE                      = "EYB"
USER_LOGGED_OFF                      = "UOFF"


# empty string means listen on any host
HOST = ''

END_OF_MESSAGE_SEQUENCE = '\r\n\r\n'

VERBOSE = False

running = True

MOTD = ''

# elements are of the form (conn, msg)
# conn is the socket object that sent us the message
# msg is a Message object
unprocessed_messages = Queue()

# conn_info[conn] = ConnectionInfo
conn_info = {}


class ConnectionState(Enum):
    CONNECTING = auto()
    CONNECTED = auto()
    LOGGED_IN = auto()
    QUITTING = auto()


class ConnectionInfo(object):
    def __init__(self, conn):
        self.conn = conn
        self.username = None
        self.state = ConnectionState.CONNECTING
        self.incoming_data = ''
        self.closed = False
        self.received = []

    def valid_receive_response(self, msg):
        for msg_r in self.received:
            if msg_r.username == msg.username:
                self.received.remove(msg_r)
                return msg_r

    def close(self):
        self.closed = True

    def connecting(self):
        return self.state == ConnectionState.CONNECTING

    def connected(self):
        return self.state == ConnectionState.CONNECTED

    def logged_in(self):
        return self.state == ConnectionState.LOGGED_IN

    def quitting(self):
        return self.state == ConnectionState.QUITTING


class Message(object):
    def __init__(self, command, username='', message='', users=''):
        self.command = command
        self.username = username
        self.message = message
        self.users = users

    def __str__(self):
        if self.command == CONNECT:
            return CONNECT

        if self.command == CONNECT_RESPONSE:
            return CONNECT_RESPONSE

        if self.command == REGISTER_USERNAME:
            return '{} {}'.format(REGISTER_USERNAME, self.username)

        if self.command == REGISTER_USERNAME_RESPONSE_TAKEN:
            return REGISTER_USERNAME_RESPONSE_TAKEN

        if self.command == REGISTER_USERNAME_RESPONSE_SUCCESS:
            return REGISTER_USERNAME_RESPONSE_SUCCESS

        if self.command == DAILY_MESSAGE:
            return '{} {}'.format(DAILY_MESSAGE, self.message)

        if self.command == LIST_USERS:
            return LIST_USERS

        if self.command == LIST_USERS_RESPONSE:
            return '{} {}'.format(LIST_USERS_RESPONSE, ' '.join(self.users))

        if self.command == SEND_MESSAGE:
            return '{} {} {}'.format(SEND_MESSAGE, self.username, self.message)

        if self.command == SEND_MESSAGE_RESPONSE_SUCCESS:
            return '{} {}'.format(SEND_MESSAGE_RESPONSE_SUCCESS, self.username)

        if self.command == SEND_MESSAGE_RESPONSE_DOES_NOT_EXIST:
            return '{} {}'.format(SEND_MESSAGE_RESPONSE_DOES_NOT_EXIST, self.username)

        if self.command == RECEIVE_MESSAGE:
            return '{} {} {}'.format(RECEIVE_MESSAGE, self.username, self.message)

        if self.command == RECEIVE_MESSAGE_SUCCESS:
            return '{} {}'.format(RECEIVE_MESSAGE_SUCCESS, self.username)

        if self.command == LOGOUT:
            return LOGOUT

        if self.command == LOGOUT_RESPONSE:
            return LOGOUT_RESPONSE

        if self.command == USER_LOGGED_OFF:
            return '{} {}'.format(USER_LOGGED_OFF, self.username)

    def encode(self):
        msg = str(self) + END_OF_MESSAGE_SEQUENCE
        return msg.encode()

    @classmethod
    def parse(cls, msg):
        if msg.startswith(CONNECT):
            return Message(command=CONNECT)

        elif msg.startswith(REGISTER_USERNAME):
            command, username = msg.split(' ', 2)
            return Message(command=REGISTER_USERNAME, username=username)

        elif msg.startswith(LIST_USERS):
            return Message(command=LIST_USERS)

        elif msg.startswith(SEND_MESSAGE):
            command, username, message = msg.split(' ', 3)
            return Message(command=SEND_MESSAGE, username=username, message=message)

        elif msg.startswith(RECEIVE_MESSAGE_SUCCESS):
            command, username = msg.split(' ', 2)
            return Message(command=RECEIVE_MESSAGE_SUCCESS, username=username)

        elif msg.startswith(LOGOUT):
            return Message(command=LOGOUT)

        else:
            return None


def read_data(conn):
    buf = conn.recv(4096).decode()

    if len(buf) == 0:
        raise EOFError('connection closed')

    conn_info[conn].incoming_data += buf


def get_messages(conn):
    messages = []

    buf = conn_info[conn].incoming_data

    start = 0
    end = buf.find(END_OF_MESSAGE_SEQUENCE, start)

    while end != -1:
        messages.append(buf[start:end])

        start = end + len(END_OF_MESSAGE_SEQUENCE)
        end = buf.find(END_OF_MESSAGE_SEQUENCE, start)

    conn_info[conn].incoming_data = buf[start:]

    return messages


def list_diff(a, b):
    b = set(b)
    return [x for x in a if x not in b]


def process_server_command(command):
    global running

    if command == '/users':
        users = [c_info.username for c_info in conn_info if c_info.username] or ['No users online']
        print('\n'.join(users))

    elif command == '/help':
        print('/users     Displays a list of all online users')
        print('/help      Displays this help message')
        print('/shutdown  Shutdown the server')

    elif command == '/shutdown':
        running = False

    else:
        print('Invalid command')


def start_server(port_number):
    with socket.socket(socket.AF_INET) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, port_number))
        s.listen()

        poll = select.poll()
        poll.register(s, select.POLLIN)
        poll.register(sys.stdin, select.POLLIN)

        while running:
            # clean up closed connections
            expired_conns = [c_info.conn for c_info in conn_info.values() if c_info.closed]
            for conn in expired_conns:
                poll.unregister(conn)
                del conn_info[conn]
                conn.close()


            for fd, event in poll.poll(200):
                # new incoming connection
                if fd == s.fileno():
                    conn, addr = s.accept()
                    poll.register(conn, select.POLLIN)
                    conn_info[conn] = ConnectionInfo(conn)

                # read from stdin
                if fd == sys.stdin.fileno():
                    command = sys.stdin.readline().strip()
                    process_server_command(command)

                # new message from existing connection
                for conn in conn_info:
                    if fd == conn.fileno():
                        # read all available data from the socket
                        try:
                            read_data(conn)

                        # the socket was closed
                        except EOFError:
                            poll.unregister(conn)
                            del conn_info[conn]
                            conn.close()
                            break

                    # parse all available messages
                    messages = get_messages(conn)

                    # add the messages to the queue
                    for raw_msg in messages:
                        msg = Message.parse(raw_msg)

                        # valid message
                        if msg:
                            unprocessed_messages.put((conn, msg))

                        # invalid message (close the connection)
                        else:
                            poll.unregister(conn)
                            conn.close()


        for conn in conn_info:
            conn.close()


def send_message(conn, msg):
    if VERBOSE:
        print(msg)
    conn.sendall(msg.encode())


def username_taken(username):
    for c_info in conn_info.values():
        if c_info.username == username:
            return True
    return False


def get_conn_info_by_username(username):
    for c_info in conn_info.values():
        if c_info.username == username and not c_info.closed:
            return c_info
    return None


def get_open_connections():
    return [c_info.conn for c_info in conn_info.values() if not c_info.closed]


def process_message(conn, msg):
    if msg.command == CONNECT and conn_info[conn].connecting():
        reply = Message(CONNECT_RESPONSE)
        send_message(conn, reply)
        conn_info[conn].state = ConnectionState.CONNECTED

    elif msg.command == REGISTER_USERNAME and conn_info[conn].connected():
        if len(msg.username) > 10:
            conn_info[conn].close()

        elif username_taken(msg.username):
            reply = Message(REGISTER_USERNAME_RESPONSE_TAKEN)
            send_message(conn, reply)

        else:
            reply = Message(REGISTER_USERNAME_RESPONSE_SUCCESS)
            send_message(conn, reply)

            reply = Message(DAILY_MESSAGE, message=MOTD)
            send_message(conn, reply)

            conn_info[conn].username = msg.username
            conn_info[conn].state = ConnectionState.LOGGED_IN

    elif msg.command == LIST_USERS and conn_info[conn].logged_in():
        users = [c_info.username for c_info in conn_info.values() if c_info.username]

        reply = Message(LIST_USERS_RESPONSE, users=users)
        send_message(conn, reply)

    elif msg.command == SEND_MESSAGE and conn_info[conn].logged_in():
        recv_conn_info = get_conn_info_by_username(msg.username)

        if not recv_conn_info:
            reply = Message(SEND_MESSAGE_RESPONSE_DOES_NOT_EXIST, username=msg.username)
            send_message(conn, reply)

        else:
            from_msg = Message(RECEIVE_MESSAGE, username=conn_info[conn].username, message=msg.message)
            send_message(recv_conn_info.conn, from_msg)
            recv_conn_info.received.append(from_msg)

    elif msg.command == RECEIVE_MESSAGE_SUCCESS and conn_info[conn].logged_in():
        sender_conn_info = get_conn_info_by_username(msg.username)

        if conn_info[conn].valid_receive_response(msg):
            sender_reply = Message(SEND_MESSAGE_RESPONSE_SUCCESS, username=conn_info[conn].username)
            send_message(sender_conn_info.conn, sender_reply)

        else:
            conn.close()

    elif msg.command == LOGOUT and conn_info[conn].logged_in():
        reply = Message(LOGOUT_RESPONSE)
        send_message(conn, reply)

        conn_info[conn].close()

        broadcast = Message(USER_LOGGED_OFF, username=conn_info[conn].username)
        for conn in get_open_connections():
            send_message(conn, broadcast)


def worker_thread():
    while True:
        try:
            conn, msg = unprocessed_messages.get()

            if VERBOSE:
                print(msg)

            process_message(conn, msg)

        except Exception as e:
            raise e
            continue

        finally:
            unprocessed_messages.task_done()



def start_workers(num_workers):
    for _ in range(num_workers):
        t = Thread(target=worker_thread, daemon=True)
        t.start()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', dest='verbose', action='store_true', help='Verbose print all incoming and outgoing protocol verbs & content.')
    parser.add_argument('port_number', type=int, help='Port number to listen on.')
    parser.add_argument('num_workers', type=int, help='Number of workers to spawn.')
    parser.add_argument('motd', help='Message to display to the client when they connect.')

    args = parser.parse_args()

    VERBOSE = args.verbose
    MOTD = args.motd

    start_workers(args.num_workers)
    start_server(args.port_number)
