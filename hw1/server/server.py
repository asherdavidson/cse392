import socket
import argparse
import select

from queue import Queue
from threading import Thread


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

# elements are of the form (conn, msg)
# conn is the socket object that sent us the message
# msg is a Message object
unprocessed_messages = Queue()

# incoming data is stored by conn object
# i.e. incoming_data[conn] = '<data>'
incoming_data = {}


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

    if conn in incoming_data:
        incoming_data[conn] += buf

    else:
        incoming_data[conn] = buf


def get_messages(conn):
    messages = []

    buf = incoming_data.get(conn, '')

    start = 0
    end = buf.find(END_OF_MESSAGE_SEQUENCE, start)

    while end != -1:
        messages.append(buf[start:end])

        start = end + len(END_OF_MESSAGE_SEQUENCE)
        end = buf.find(END_OF_MESSAGE_SEQUENCE, start)

    incoming_data[conn] = buf[start:]

    return messages


def start_server(port_number, motd, verbose):
    with socket.socket(socket.AF_INET) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, port_number))
        s.listen()

        poll = select.poll()
        poll.register(s, select.POLLIN)

        client_conns = []

        while True:
            for fd, event in poll.poll():
                print(fd, event)

                # new incoming connection
                if fd == s.fileno():
                    conn, addr = s.accept()
                    client_conns.append(conn)
                    poll.register(conn, select.POLLIN)

                # new message from existing connection
                for conn in client_conns:
                    if fd == conn.fileno():
                        # read all available data from the socket
                        try:
                            read_data(conn)

                        # the socket was closed
                        except EOFError:
                            poll.unregister(conn)
                            client_conns.remove(conn)
                            conn.close()

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
                            client_conns.remove(conn)
                            conn.close()


        for conn in client_conns:
            conn.close()


def worker_thread():
    running = True

    while running:
        conn, msg = unprocessed_messages.get()

        print(msg)
        conn.sendall(msg.encode())

        unprocessed_messages.task_done()


def start_workers(num_workers, verbose):
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

    print(args)

    print('POLLIN', select.POLLIN)
    print('POLLPRI', select.POLLPRI)
    print('POLLOUT', select.POLLOUT)
    print('POLLERR', select.POLLERR)
    print('POLLHUP', select.POLLHUP)
    print('POLLRDHUP', select.POLLRDHUP)
    print('POLLNVAL', select.POLLNVAL)

    start_workers(args.num_workers, args.verbose)
    start_server(args.port_number, args.motd, args.verbose)