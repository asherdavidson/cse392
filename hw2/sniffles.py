import argparse
import socket
import fcntl

from hexdump import hexdump, dump

from packet_types import *

ETH_P_ALL = 0x0003


def sniff(interface, timeout, dumphex, filter):
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(ETH_P_ALL))
    s.bind((interface, 0))

    while True:
        buf = s.recv(4096)

        if dumphex:
            hexdump(buf)
            print()
            # print(hexdump.dump(buf))

        else:
            try:
                packet = Packet(buf)

                if filter:
                    if packet.get_matching_layer(filter):
                        print(packet.get_matching_layer(filter))
                else:
                    print(packet)

            except:
                print('Error parsing packet:')
                hexdump(buf)
                print()

    s.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output', help='File name to output to')
    parser.add_argument('-t', '--timeout', help='Amount of time to capture for before quitting. If no\
                                                 time specified ^C must be sent to close program')
    parser.add_argument('-x', '--hexdump', action='store_true', help='Print hexdump to stdout')
    # TODO: ONE_MORE_OF_YOUR_CHOOSING
    parser.add_argument('-f', '--filter', choices=['UDP', 'Ethernet', 'DNS', 'IP', 'TCP', 'ONE_MORE_OF_YOUR_CHOOSING'], help='Filter for one specified protocol')
    parser.add_argument('interface', help='interface to listen for traffic on')

    args = parser.parse_args()
    print(args)

    sniff(args.interface, args.timeout, args.hexdump, args.filter)
