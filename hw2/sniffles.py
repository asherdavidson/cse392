import argparse
import socket
import fcntl
import signal

from hexdump import hexdump, dump
from construct import *

from packet_types import *

ETH_P_ALL = 0x0003

section_header_block = Struct(
    'block_type' / Const(bytes.fromhex('0A0D0D0A'), Bytes(4)),
    'block_total_length' / Const(28, BytesInteger(4)),
    'byte_order_magic' / Const(bytes.fromhex('1A2B3C4D'), Bytes(4)),
    'major_version' / Const(1, BytesInteger(2)),
    'minor_version' / Const(0, BytesInteger(2)),
    'section_length' / Const(-1, Int64sn),  # TODO
    # 'options' / BytesInteger(),  # TODO
    'block_total_length' / Const(28, BytesInteger(4)),
)

interface_description_block = Struct(
    'block_type' / Const(bytes.fromhex('00000001'), Bytes(4)),
    'block_total_length' / Const(20, BytesInteger(4)),
    'link_type' / Const(1, BytesInteger(2)),
    'reserved' / Padding(2),
    'snap_len' / Const(0, BytesInteger(4)),
    # 'options' /
    'block_total_length' / Const(20, BytesInteger(4)),
)

enhanced_packet_block = Struct(
    'block_type' / Const(bytes.fromhex('00000006'), Bytes(4)),
    'block_total_length' / Rebuild(Bytes(4), lambda this: 32 + this.captured_packet_length),
    'interface_id' / Const(0, BytesInteger(4)),
    'timestamp' / BytesInteger(8),
    'captured_packet_length' / BytesInteger(4),
    'original_packet_length' / BytesInteger(4),
    'packet_data' / Aligned(4, Bytes(this.captured_packet_length)),
    # 'options' /
    'block_total_length' / Rebuild(Bytes(4), lambda this: 32 + this.captured_packet_length),
)


def exit_handler(signum, frame):
    raise SystemExit()


def export_packets(filename, packets):
    with open(filename, 'wb') as f:
        shb = section_header_block.build({})
        f.write(shb)

        idb = interface_description_block.build({})
        f.write(idb)

        for p in packets:
            epb = enhanced_packet_block.build(p.enhanced_packet_data())
            f.write(epb)


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

    except Exception:
        print('Error parsing packet:')
        hexdump(buf)
        print()

        return None


def sniff(interface, timeout, dumphex, filter, filename):
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
        if filename:
            export_packets(filename, packets)
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

    sniff(args.interface, args.timeout, args.hexdump, args.filter, args.output)
