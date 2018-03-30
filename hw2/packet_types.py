from time import time

from construct import *
from hexdump import hexdump, dump

import constants


def hex(s):
    return f'0x{s:x}'

def pretty_print(classname, args):
    temp = []
    for name, value in args.items():
        temp.append(f'{name}={repr(value)}')
    values = ', '.join(temp)

    return f'{classname}({values})'


def format_ipv4_address(addr):
    return f'{addr[0]}.{addr[1]}.{addr[2]}.{addr[3]}'


def format_flags(flags):
    temp = []
    for flag, is_true in flags.items():
        if is_true and not flag.startswith('_'):
            temp.append(flag)
    values = ', '.join(temp)
    return f'{{{values}}}'


class Packet(object):
    def __init__(self, buf):
        self.buf = buf
        self.timestamp = time()

        self.data_link_layer = Ethernet(buf)
        self.network_layer = self.data_link_layer.network_layer

        if self.network_layer.transport_layer:
            self.transport_layer = self.network_layer.transport_layer
        else:
            self.transport_layer = None

        if self.transport_layer.application_layer:
            self.application_layer = self.transport_layer.application_layer
        else:
            self.application_layer = None

    def __str__(self):
        if self.application_layer:
            return str(self.application_layer)

        if self.transport_layer:
            return str(self.transport_layer)

        if self.network_layer:
            return str(self.network_layer)

        return str(self.data_link_layer)

    def enhanced_packet_data(self):
        return {
            'timestamp': int(self.timestamp * 10 ** 6),
            'captured_packet_length': len(self.buf),
            'original_packet_length': len(self.buf),
            'packet_data': self.buf,
        }

    def get_matching_layer(self, filter):
        """Returns None if no layer matches"""
        if filter == self.data_link_layer.__class__.__name__:
            return self.data_link_layer

        if filter == 'IP' and self.network_layer.__class__.__name__ in ['IPv4', 'IPv6']:
            return self.network_layer

        if filter == self.transport_layer.__class__.__name__:
            return self.transport_layer

        if filter == self.application_layer.__class__.__name__:
            return self.application_layer

        return None


class Layer(object):
    def __init__(self, buf):
        remaining_bytes = self.parse(buf)
        self.process_next_layer(remaining_bytes)

    def parse(self, buf):
        raise NotImplementedError()

    def process_next_layer(self):
        raise NotImplementedError()


#########################
# Layer 7 (Application) #
#########################


class ApplicationLayer(Layer):
    pass


class DNS(ApplicationLayer):
    dns_header_struct = BitStruct(
        'id' / BitsInteger(16),
        'qr' / BitsInteger(1),
        'opcode' / BitsInteger(4),
        'flags' / FlagsEnum(BitsInteger(4),
            AA = 0x1 << 3,
            TC = 0x1 << 2,
            RD = 0x1 << 1,
            RA = 0x1 << 0,
        ),
        'z' / BitsInteger(3),  # reserved
        'rcode' / BitsInteger(4),
    )

    dns_header_counts = Struct(
        'qd_count' / Short,
        'an_count' / Short,
        'ns_count' / Short,
        'ar_count' / Short
    )

    segment_struct = Struct(
        'pad' /  Peek(Byte),       # 11 = pointer 00 = segment
        'name' / IfThenElse(this.pad > 63, Short, PascalString(Byte, "ascii"))
    )

    dns_question_struct = Struct(
        'qname' / RepeatUntil(len_(obj_) == 0, PascalString(Byte, "ascii")),
        'qtype' / Short,
        'qclass' / Short
    )

    resource_record_struct = Struct(
        'name'  / RepeatUntil(lambda obj, lst, ctx: obj_.pad > 63 or obj_.pad == 0, segment_struct),
        'type' / Short,
        'class' / Short,
        'ttl' / Int,
        'rdlength' / Short,
        'rddata' / Bytes(this.rdlength)
    )

    dns_struct = Struct(
        'counts' / dns_header_counts,
        'question' / Array(this.counts.qd_count, dns_question_struct),
        'answer'  / Array(this.counts.an_count, resource_record_struct),
        'authority' / Array(this.counts.ns_count, resource_record_struct),
        'additional' / Array(this.counts.ar_count, resource_record_struct)
    )

    def parse(self, buf):
        dns_header = DNS.dns_header_struct.parse(buf)
        dns = DNS.dns_struct.parse(buf[4:])

        self.id       = dns_header.id
        self.qr       = dns_header.qr
        self.opcode   = dns_header.flags
        self.z        = dns_header.z
        self.rcode    = dns_header.rcode
        self.qd_count = dns.counts.qd_count
        self.an_count = dns.counts.an_count
        self.ns_count = dns.counts.ns_count
        self.ar_count = dns.counts.ar_count

        self.question   = dns.question
        self.answer     = dns.answer
        self.authority  = dns.authority
        self.additional = dns.additional

    def process_next_layer(self, remaining_bytes):
        return

    def __str__(self):
        args = {
            'id':       self.id,
            'qr':       self.qr,
            'opcode':   self.opcode,
            'z':        self.z,
            'rcode':    self.rcode,
            'qd_count': self.qd_count,
            'an_count': self.an_count,
            'ns_count': self.ns_count,
            'ar_count': self.ar_count,

            # not sure how this will print yet..
            'question':     self.question,
            'answer':       self.answer,
            'authority':    self.authority,
            'additional':   self.additional
        }

        return pretty_print('DNS', args)

# by port number
ApplicationLayerTypes = {
   53 : DNS   # Most DNS is over UDP
}


#######################
# Layer 4 (Transport) #
#######################


class TransportLayer(Layer):
    def process_next_layer(self, remaining_bytes):
        self.application_layer = None
        if ApplicationLayerTypes.get(self.dest_port):
            self.application_layer = ApplicationLayerTypes[self.dest_port](remaining_bytes)

        elif ApplicationLayerTypes.get(self.source_port):
            self.application_layer = ApplicationLayerTypes[self.source_port](remaining_bytes)


class TCP(TransportLayer):
    tcp_struct = BitStruct(
        'source_port' / BitsInteger(16),
        'dest_port' / BitsInteger(16),
        'seq_number' / BitsInteger(32),
        'ack_number' / BitsInteger(32),
        'data_offset' / BitsInteger(4),
        'reserved' / BitsInteger(3),
        'flags' / FlagsEnum(BitsInteger(9),
            NS  = 0x1 << 8,
            CWR = 0x1 << 7,
            ECE = 0x1 << 6,
            URG = 0x1 << 5,
            ACK = 0x1 << 4,
            PSH = 0x1 << 3,
            RST = 0x1 << 2,
            SYN = 0x1 << 1,
            FIN = 0x1 << 0,
        ),
        'window_size' / BitsInteger(16),
        'checksum' / BitsInteger(16),
        'urgent_pointer' / BitsInteger(16),
        'options' / BitsInteger(lambda this: (this.data_offset-5)*32)
    )

    def parse(self, buf):
        tcp = TCP.tcp_struct.parse(buf)

        self.source_port    = tcp.source_port
        self.dest_port      = tcp.dest_port
        self.seq_number     = tcp.seq_number
        self.ack_number     = tcp.ack_number
        self.data_offset    = tcp.data_offset
        self.reserved       = tcp.reserved
        self.flags          = tcp.flags
        self.window_size    = tcp.window_size
        self.checksum       = tcp.checksum
        self.urgent_pointer = tcp.urgent_pointer
        self.options        = tcp.options
        self.options_length = (tcp.data_offset-5)*4

        return buf[tcp.data_offset*4:]

    def __str__(self):
        args = {
            'src_port':    self.source_port,
            'dst_port':    self.dest_port,
            'seq_num':     hex(self.seq_number),
            'ack_num':     hex(self.ack_number),
            'data_offset': self.data_offset,
            'flags':       format_flags(self.flags),
            'win_size':    self.window_size,
            'checksum':    hex(self.checksum),
            'urgent_ptr':  self.urgent_pointer,
            'options':     hex(self.options),
        }

        return pretty_print('TCP', args)


class UDP(TransportLayer):
    udp_struct = BitStruct(
        'source_port' / BitsInteger(16),
        'dest_port' / BitsInteger(16),
        'length' / BitsInteger(16),
        'checksum' / BitsInteger(16)
    )

    def parse(self, buf):
        udp = UDP.udp_struct.parse(buf)

        self.source_port = udp.source_port
        self.dest_port   = udp.dest_port
        self.length      = udp.length
        self.checksum    = udp.checksum

        return buf[8:]

    def __str__(self):
        args = {
            'src_port':    self.source_port,
            'dst_port':    self.dest_port,
            'length':      hex(self.length),
            'checksum':    hex(self.checksum)
        }

        return pretty_print('UDP', args)


TransportLayerTypes = {
    6: TCP,
    17: UDP,
}

#####################
# Layer 3 (Network) #
#####################


class NetworkLayer(Layer):
    pass


class IPv4(NetworkLayer):
    ipv4_struct = BitStruct(
        'version' / BitsInteger(4),
        'IHL' / BitsInteger(4),  # Internet Header Length
        'DSCP' / BitsInteger(6),  # Differentiated Services Code Point
        'ECN' / BitsInteger(2),  # Explicit Congestion Notification
        'total_length' / BitsInteger(16),
        'identification' / BitsInteger(16),
        'flags' / FlagsEnum(BitsInteger(3),
            DF = 2,  # Don't fragment
            MF = 4,  # More fragments
        ),
        'fragment_offset' / BitsInteger(13),
        'ttl' / BitsInteger(8),
        'protocol' / BitsInteger(8),
        'header_checksum' / BitsInteger(16),
        'source_ip' / constants.IPv4Address,
        'dest_ip' / constants.IPv4Address,
        'options' / BitsInteger(lambda this: (this.IHL-5)*32),
    )

    protocols = constants.IPv4_protocols

    def parse(self, buf):
        ipv4 = IPv4.ipv4_struct.parse(buf)

        self.version         = ipv4.version
        self.IHL             = ipv4.IHL
        self.DSCP            = ipv4.DSCP
        self.ECN             = ipv4.ECN
        self.total_length    = ipv4.total_length
        self.identification  = ipv4.identification
        self.flags           = ipv4.flags
        self.fragment_offset = ipv4.fragment_offset
        self.ttl             = ipv4.ttl
        self.protocol        = ipv4.protocol
        self.header_checksum = ipv4.header_checksum
        self.source_ip       = ipv4.source_ip
        self.dest_ip         = ipv4.dest_ip
        self.options         = ipv4.options

        return buf[(ipv4.IHL*4):]

    def process_next_layer(self, remaining_bytes):
        self.transport_layer = None
        if TransportLayerTypes.get(self.protocol):
            self.transport_layer = TransportLayerTypes[self.protocol](remaining_bytes)

    def __str__(self):
        if self.protocol >= 143 and self.protocol <= 252:
            protocol = 'UNASSIGNED'
        elif self.protocol >= 253 and self.protocol <= 254:
            protocol = 'Experimental'
        else:
            protocol = IPv4.protocols.get(self.protocol, 'Unknown')

        args = {
            # 'version':         self.version,
            'IHL':             self.IHL,
            'DSCP':            self.DSCP,
            'ECN':             self.ECN,
            'total_length':    self.total_length,
            'identification':  self.identification,
            'flags':           format_flags(self.flags),
            'fragment_offset': self.fragment_offset,
            'ttl':             self.ttl,
            'protocol':        protocol,
            'header_checksum': self.header_checksum,
            'source_ip':       format_ipv4_address(self.source_ip),
            'dest_ip':         format_ipv4_address(self.dest_ip),
        }
        if self.options:
            args['options'] = hex(self.options)

        return pretty_print('IPv4', args)


NetworkLayerTypes = {
    0x0800: IPv4,
    # 0x0806: ARP,
    # 0x86DD: IPv6
}


#######################
# Layer 2 (Data Link) #
#######################


class DataLinkLayer(Layer):
    pass


class Ethernet(DataLinkLayer):
    struct = Struct(
        'destination' / BytesInteger(6),
        'source' / BytesInteger(6),
        'type' / BytesInteger(2)
    )

    # http://www.iana.org/assignments/ieee-802-numbers/ieee-802-numbers.xhtml#ieee-802-numbers-1
    types = {
        0x0800: 'IPv4',
        0x0806: 'ARP',
        0x86DD: 'IPv6'
    }

    def parse(self, buf):
        ethernet_header = buf[:14]
        ethernet_header_struct = Ethernet.struct.parse(ethernet_header)

        self.destination = ethernet_header_struct.destination
        self.source      = ethernet_header_struct.source
        self.type        = ethernet_header_struct.type

        return buf[14:]

    def process_next_layer(self, remaining_bytes):
        self.network_layer = None
        if NetworkLayerTypes.get(self.type):
            self.network_layer = NetworkLayerTypes[self.type](remaining_bytes)

    def __str__(self):
        args = {
            'destination': dump(Ethernet.struct.destination.build(self.destination)),
            'source':      dump(Ethernet.struct.source.build(self.source)),
            'type':        Ethernet.types.get(self.type, 'Unknown'),

        }

        return pretty_print('Ethernet', args)
