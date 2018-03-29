import argparse
import socket
import fcntl
import signal

from hexdump import hexdump, dump

from packet_types import *

ETH_P_ALL = 0x0003


def exit_handler(signum, frame):
    raise SystemExit()


def process_packet(buf, filter, dumphex):
    try:
        packet = Packet(buf)

        if filter:
            if packet.get_matching_layer(filter):
                if dumphex:
                    hexdump(buf)
                    print()
                else:
                    print(packet.get_matching_layer(filter))
        else:
            if dumphex:
                hexdump(buf)
                print()
            else:
                print(packet)

        return packet

    except:
        print('Error parsing packet:')
        hexdump(buf)
        print()

        return None


def sniff(interface, timeout, dumphex, filter):
    # setup exit handlers
    signal.signal(signal.SIGINT, exit_handler)
    if timeout:
        signal.signal(signal.SIGALRM, exit_handler)
        signal.alarm(timeout)

    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(ETH_P_ALL))
    s.bind((interface, 0))

    packets = []

    try:
        while True:
            buf = s.recv(4096)

            packet = process_packet(buf, filter, dumphex)
            if packet:
                packets.append(packet)

    except SystemExit:
        print()

    s.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output', help='File name to output to')
    parser.add_argument('-t', '--timeout', type=int, help='Amount of time to capture for before quitting. If no\
                                                           time specified ^C must be sent to close program')
    parser.add_argument('-x', '--hexdump', action='store_true', help='Print hexdump to stdout')
    # TODO: ONE_MORE_OF_YOUR_CHOOSING
    parser.add_argument('-f', '--filter', choices=['UDP', 'Ethernet', 'DNS', 'IP', 'TCP', 'ARP'], help='Filter for one specified protocol')
    parser.add_argument('interface', help='interface to listen for traffic on')

    args = parser.parse_args()

    sniff(args.interface, args.timeout, args.hexdump, args.filter)
