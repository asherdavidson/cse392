from construct import *

IPv4Address = Sequence(
        BitsInteger(8),
        BitsInteger(8),
        BitsInteger(8),
        BitsInteger(8)
)

IPv4_protocols = {
    0: 'HOPOPT',
    1: 'ICMP',
    2: 'IGMP',
    3: 'GGP',
    4: 'IP',
    5: 'ST',
    6: 'TCP',
    7: 'CBT',
    8: 'EGP',
    9: 'IGP',
    10: 'BBN',
    11: 'NVP',
    12: 'PUP',
    13: 'ARGUS',
    14: 'EMCON',
    15: 'XNET',
    16: 'CHAOS',
    17: 'UDP',
    18: 'MUX',
    19: 'DCN',
    20: 'HMP',
    21: 'PRM',
    22: 'XNS',
    23: 'TRUNK',
    24: 'TRUNK',
    25: 'LEAF',
    26: 'LEAF',
    27: 'RDP',
    28: 'IRTP',
    29: 'ISO',
    30: 'NETBLT',
    31: 'MFE',
    32: 'MERIT',
    33: 'DCCP',
    34: 'PC',
    35: 'IDPR',
    36: 'XTP',
    37: 'DDP',
    38: 'IDPR',
    39: 'TP',
    40: 'IL',
    41: 'IPv6',
    42: 'SDRP',
    43: 'IPv6',
    44: 'IPv6',
    45: 'IDRP',
    46: 'RSVP',
    47: 'GREs',
    48: 'DSR',
    49: 'BNA',
    50: 'ESP',
    51: 'AH',
    52: 'I',
    53: 'SWIPE',
    54: 'NARP',
    55: 'MOBILE',
    56: 'TLSP',
    57: 'SKIP',
    58: 'IPv6',
    59: 'IPv6',
    60: 'IPv6',
    61: 'Any host internal protocol',
    62: 'CFTP',
    63: 'Any local network',
    64: 'SAT',
    65: 'KRYPTOLAN',
    66: 'RVD',
    67: 'IPPC',
    68: 'Any distributed file system',
    69: 'SAT',
    70: 'VISA',
    71: 'IPCU',
    72: 'CPNX',
    73: 'CPHB',
    74: 'WSN',
    75: 'PVP',
    76: 'BR',
    77: 'SUN',
    78: 'WB',
    79: 'WB',
    80: 'ISO',
    81: 'VMTP',
    82: 'SECURE',
    83: 'VINES',
    84: 'TTP',
    84: 'IPTM',
    85: 'NSFNET',
    86: 'DGP',
    87: 'TCF',
    88: 'EIGRP',
    89: 'OSPF',
    90: 'Sprite',
    91: 'LARP',
    92: 'MTP',
    93: 'AX',
    94: 'OS',
    95: 'MICP',
    96: 'SCC',
    97: 'ETHERIP',
    98: 'ENCAP',
    99: 'Any private encryption scheme',
    100: 'GMTP',
    101: 'IFMP',
    102: 'PNNI',
    103: 'PIM',
    104: 'ARIS',
    105: 'SCPS',
    106: 'QNX',
    107: 'A',
    108: 'IPComp',
    109: 'SNP',
    110: 'Compaq',
    111: 'IPX',
    112: 'VRRP',
    113: 'PGM',
    114: 'Any 0-hop protocol',
    115: 'L2TP',
    116: 'DDX',
    117: 'IATP',
    118: 'STP',
    119: 'SRP',
    120: 'UTI',
    121: 'SMP',
    122: 'SM',
    123: 'PTP',
    124: 'IS',
    125: 'FIRE',
    126: 'CRTP',
    127: 'CRUDP',
    128: 'SSCOPMCE',
    129: 'IPLT',
    130: 'SPS',
    131: 'PIPE',
    132: 'SCTP',
    133: 'FC',
    134: 'RSVP-E2E-IGNORE',
    135: 'Mobility',
    136: 'UDPLite',
    137: 'MPLS-in-IP',
    138: 'manet',
    139: 'HIP',
    140: 'Shim6',
    141: 'WESP',
    142: 'ROHC',
    255: 'Reserved for extra',
}