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
    """Client socket connection states"""
    CONNECTING = auto()
    CONNECTED = auto()
    LOGGED_IN = auto()
    QUITTING = auto()


class ConnectionInfo(object):
    """State for each connection"""
    def __init__(self, conn):
        self.conn = conn  # socket
        self.username = None
        self.state = ConnectionState.CONNECTING
        self.incoming_data = ''  # received data buffer
        self.closed = False
        self.received = []  # messages this user needs to confirm

    def valid_receive_response(self, msg):
        """Checks if the received confirmation is valid"""
        for msg_r in self.received:
            if msg_r.username == msg.username:
                self.received.remove(msg_r)
                return msg_r

    def close(self):
        """Marks the socket as closed to be cleaned up by the main thread"""
        self.closed = True

    def connecting(self):
        """Checks if the state is CONNECTING"""
        return self.state == ConnectionState.CONNECTING

    def connected(self):
        """Checks if the state is CONNECTED"""
        return self.state == ConnectionState.CONNECTED

    def logged_in(self):
        """Checks if the state is LOGGED_IN"""
        return self.state == ConnectionState.LOGGED_IN

    def quitting(self):
        """Checks if the state is QUITTING"""
        return self.state == ConnectionState.QUITTING


class Message(object):
    """Parses and encodes messages"""
    def __init__(self, command, username='', message='', users=''):
        self.command = command
        self.username = username
        self.message = message
        self.users = users

    def __str__(self):
        """Converts the message into the protocol format"""
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
        """Converts the message object into the protocol format
        and turns it into a bytes object."""
        msg = str(self) + END_OF_MESSAGE_SEQUENCE
        return msg.encode()

    @classmethod
    def parse(cls, msg):
        """Parses a string into a message.
        Returns None if the message is invalid"""
        if msg.startswith(CONNECT):
            return Message(command=CONNECT)

        elif msg.startswith(REGISTER_USERNAME):
            parts = msg.split(' ', 2)
            if len(parts) != 2:
                return None
            command, username = parts
            return Message(command=REGISTER_USERNAME, username=username)

        elif msg.startswith(LIST_USERS):
            return Message(command=LIST_USERS)

        elif msg.startswith(SEND_MESSAGE):
            parts = msg.split(' ', 3)
            if len(parts) != 3:
                return None
            command, username, message = parts
            return Message(command=SEND_MESSAGE, username=username, message=message)

        elif msg.startswith(RECEIVE_MESSAGE_SUCCESS):
            parts = msg.split(' ', 2)
            if len(parts) != 2:
                return None
            command, username = parts
            return Message(command=RECEIVE_MESSAGE_SUCCESS, username=username)

        elif msg.startswith(LOGOUT):
            return Message(command=LOGOUT)

        else:
            return None


def read_data(conn):
    """Reads up to 4096 bytes from the socket.
    The data is stored in the sockets incoming_data buffer.
    Raises EOFError if the connection is closed."""
    buf = conn.recv(4096).decode()

    if len(buf) == 0:
        raise EOFError('connection closed')

    conn_info[conn].incoming_data += buf


def get_messages(conn):
    """Parses a connections incoming_data buffer into messages.
    Incomplete messages are left in the buffer until the remaining
    data is received.
    Returns as many parsable messages as possible."""

    messages = []

    buf = conn_info[conn].incoming_data

    # start and end indices
    start = 0
    end = buf.find(END_OF_MESSAGE_SEQUENCE, start)

    while end != -1:
        messages.append(buf[start:end])

        start = end + len(END_OF_MESSAGE_SEQUENCE)
        end = buf.find(END_OF_MESSAGE_SEQUENCE, start)

    # clean up parsed messages from the buffer
    conn_info[conn].incoming_data = buf[start:]

    return messages


def process_server_command(command):
    """Parses and runs the server cli argument"""
    global running

    # Print the users online
    if command == '/users':
        users = [c_info.username for c_info in conn_info if c_info.username] or ['No users online']
        print('\n'.join(users))

    # Print the help page
    elif command == '/help':
        print('/users     Displays a list of all online users')
        print('/help      Displays this help message')
        print('/shutdown  Shutdown the server')

    # Shutdown the server
    elif command == '/shutdown':
        running = False

    # Invalid command
    else:
        print('Invalid command')


def start_server(port_number):
    """Starts the server"""
    with socket.socket(socket.AF_INET) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # reuse freshly closed port
        s.bind((HOST, port_number))
        s.listen()

        poll = select.poll()
        poll.register(s, select.POLLIN)  # accept connections
        poll.register(sys.stdin, select.POLLIN)  # server commands

        while running:
            # clean up closed connections
            expired_conns = [c_info.conn for c_info in conn_info.values() if c_info.closed]
            for conn in expired_conns:
                poll.unregister(conn)
                del conn_info[conn]
                conn.close()


            # timeout in case the server needs to be shutdown
            for fd, event in poll.poll(200):
                # add new incoming connection
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

                    # get the raw message strings
                    messages = get_messages(conn)

                    for raw_msg in messages:
                        # parse the message
                        msg = Message.parse(raw_msg)

                        # valid message
                        if msg:
                            # add to the queue
                            unprocessed_messages.put((conn, msg))

                        # invalid message (close the connection)
                        else:
                            if VERBOSE:
                                print("Invalid message:", raw_msg)
                            poll.unregister(conn)
                            conn.close()


        # server is closing
        # clean up the remaining connections
        for conn in conn_info:
            conn.close()


def send_message(conn, msg):
    """Send a Message object across a connection.
    The message is guaranteed to be sent to completion."""
    if VERBOSE:
        print(msg)
    conn.sendall(msg.encode())


def username_taken(username):
    """Checks if the username is taken"""
    for c_info in conn_info.values():
        if c_info.username == username:
            return True
    return False


def get_conn_info_by_username(username):
    """Returns a ConnectionInfo object from a username.
    Returns None if the username is not taken."""
    for c_info in conn_info.values():
        if c_info.username == username and not c_info.closed:
            return c_info
    return None


def get_open_connections():
    """Returns the open connections (not marked closed)"""
    return [c_info.conn for c_info in conn_info.values() if not c_info.closed]


def process_message(conn, msg):
    """Processes the message and sends out any required outgoing messages"""
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
    """gets one message and processes it"""
    while True:
        try:
            conn, msg = unprocessed_messages.get()

            if VERBOSE:
                print(msg)

            process_message(conn, msg)

        except Exception as e:
            conn_info[conn].close()
            continue

        finally:
            unprocessed_messages.task_done()



def start_workers(num_workers):
    """Start the workers and mark them to close when the main thread closes"""
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

    # Set global flags
    VERBOSE = args.verbose
    MOTD = args.motd

    start_workers(args.num_workers)
    start_server(args.port_number)
