#!/usr/bin/env python3
#
# Copyright (C) 2018-2019  Maurice van der Pot <griffon26@kfk4ever.com>
#
# This file is part of taserver
# 
# taserver is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# taserver is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with taserver.  If not, see <http://www.gnu.org/licenses/>.
#

from typing import Set, Iterable
import struct
from ipaddress import IPv4Address


class AlreadyLoggedInError(Exception):
    pass


class ParseError(Exception):
    pass


class GameServerConnectedMessage():
    def __init__(self, game_server_id, game_server_ip, game_server_port, game_server_queue):
        self.game_server_id = game_server_id
        self.game_server_ip = game_server_ip
        self.game_server_port = game_server_port
        self.game_server_queue = game_server_queue


class GameServerDisconnectedMessage():
    def __init__(self, game_server_id):
        self.game_server_id = game_server_id


class HttpRequestMessage():
    def __init__(self, peer, env):
        self.peer = peer
        self.env = env


def hexparse(hexstring):
    return bytes([int('0x' + hexbyte, base=16) for hexbyte in hexstring.split()])


def _originalbytes(start, end):
    with open('resources/tribescapture.bin.stripped', 'rb') as f:
        f.seek(start)
        return f.read(end - start)


def findbytype(arr, requestedtype):
    for item in arr:
        if type(item) == requestedtype:
            return item
    return None


# ------------------------------------------------------------
# base types
# ------------------------------------------------------------

class onebyte():
    def __init__(self, ident, value=0):
        self.ident = ident
        self.value = value

    def set(self, value):
        self.value = value
        return self

    def write(self, stream):
        stream.write(struct.pack('<HB', self.ident, self.value))

    def read(self, stream):
        ident, value = struct.unpack('<HB', stream.read(3))
        if ident != self.ident:
            raise ParseError('self.ident(%02X) did not match parsed ident value (%02X)' % (self.ident, ident))
        self.value = value
        return self


class twobytes():
    def __init__(self, ident, value=0):
        self.ident = ident
        self.value = value

    def write(self, stream):
        stream.write(struct.pack('<HH', self.ident, self.value))

    def read(self, stream):
        ident, value = struct.unpack('<HH', stream.read(4))
        if ident != self.ident:
            raise ParseError('self.ident(%02X) did not match parsed ident value (%02X)' % (self.ident, ident))
        self.value = value
        return self


class fourbytes():
    def __init__(self, ident, value=0):
        self.ident = ident
        self.value = value

    def set(self, value):
        assert 0 <= value <= 0xFFFFFFFF
        self.value = value
        return self

    def write(self, stream):
        stream.write(struct.pack('<HL', self.ident, self.value))

    def read(self, stream):
        ident, value = struct.unpack('<HL', stream.read(6))
        if ident != self.ident:
            raise ParseError('self.ident(%02X) did not match parsed ident value (%02X)' % (self.ident, ident))
        self.value = value
        return self


class nbytes():
    def __init__(self, ident, valuebytes):
        self.ident = ident
        self.value = valuebytes

    def set(self, value):
        assert len(value) == len(self.value)
        self.value = value
        return self

    def write(self, stream):
        stream.write(struct.pack('<H', self.ident) + self.value)

    def read(self, stream):
        ident = struct.unpack('<H', stream.read(2))[0]
        if ident != self.ident:
            raise ParseError('self.ident(%02X) did not match parsed ident value (%02X)' % (self.ident, ident))
        self.value = stream.read(len(self.value))
        return self


class stringenum():
    def __init__(self, ident, value=''):
        self.ident = ident
        self.value = value

    def set(self, value):
        if not isinstance(value, str):
            raise ValueError('Cannot set the value of a stringenum to %s' % type(value).__name__)
        self.value = value
        return self

    def write(self, stream):
        stream.write(struct.pack('<HH', self.ident, len(self.value)) + self.value.encode('latin1'))

    def read(self, stream):
        ident, length = struct.unpack('<HH', stream.read(4))
        if ident != self.ident:
            raise ParseError('self.ident(%02X) did not match parsed ident value (%02X)' % (self.ident, ident))
        self.value = stream.read(length).decode('latin1')
        return self


class arrayofenumblockarrays():
    def __init__(self, ident):
        self.ident = ident
        self.arrays = []
        self.original_bytes = None

    def set(self, arrays):
        self.original_bytes = None
        self.arrays = arrays
        return self

    def set_original_bytes(self, start, end):
        self.original_bytes = (start, end)
        self.arrays = None
        return self

    def write(self, stream):
        if self.original_bytes:
            stream.write(_originalbytes(*self.original_bytes))
        else:
            stream.write(struct.pack('<HH', self.ident, len(self.arrays)))
            for arr in self.arrays:
                stream.write(struct.pack('<H', len(arr)))
                for enumfield in arr:
                    enumfield.write(stream)

    def read(self, stream):
        ident, length1 = struct.unpack('<HH', stream.read(4))
        if ident != self.ident:
            raise ParseError('self.ident(%02X) did not match parsed ident value (%02X)' % (self.ident, ident))
        self.arrays = []
        for _ in range(length1):
            innerarray = []
            length2 = struct.unpack('<H', stream.read(2))[0]
            for _ in range(length2):
                enumid = struct.unpack('<H', stream.peek(2))[0]
                classname = ('m%04X' % enumid).lower()
                element = globals()[classname]().read(stream)
                innerarray.append(element)
            self.arrays.append(innerarray)
        return self


class enumblockarray():
    def __init__(self, ident):
        self.ident = ident
        self.content = []

    def findbytype(self, requestedtype):
        for item in self.content:
            if type(item) == requestedtype:
                return item
        return None

    def set(self, content):
        self.content = content
        return self

    def write(self, stream):
        stream.write(struct.pack('<HH', self.ident, len(self.content)))
        for el in self.content:
            el.write(stream)

    def read(self, stream):
        ident, length = struct.unpack('<HH', stream.read(4))
        if ident != self.ident:
            raise ParseError('self.ident(%02X) did not match parsed ident value (%02X)' % (self.ident, ident))
        self.content = []
        for i in range(length):
            enumid = struct.unpack('<H', stream.peek(2))[0]
            classname = ('m%04X' % enumid).lower()
            element = globals()[classname]().read(stream)
            self.content.append(element)
        return self


class variablelengthbytes():
    def __init__(self, ident, content=b''):
        self.ident = ident
        self.content = content

    def set(self, value):
        self.content = value
        return self

    def write(self, stream):
        stream.write(struct.pack('<HL', self.ident, len(self.content)) + self.content)

    def read(self, stream):
        ident, length = struct.unpack('<HL', stream.read(6))
        if ident != self.ident:
            raise ParseError('self.ident(%04X) did not match parsed ident value (%04X)' % (self.ident, ident))
        self.content = stream.read(length)
        return self


class passwordlike(variablelengthbytes):

    def write(self, stream):
        stream.write(struct.pack('<HH', self.ident, len(self.content)) + self.content)

    def read(self, stream):
        ident, length = struct.unpack('<HH', stream.read(4))
        # Length is actually doubled due to server pass's interspersed bytes
        length = (length & 0x7FFF) * 2
        if ident != self.ident:
            raise ParseError('self.ident(%04X) did not match parsed ident value (%04X)' % (self.ident, ident))
        self.content = stream.read(length)
        return self


# ------------------------------------------------------------
# onebyte
# ------------------------------------------------------------

class m0001(onebyte):
    def __init__(self):
        super().__init__(0x0001)


# ------------------------------------------------------------
# twobytes
# ------------------------------------------------------------

class m0307(twobytes):
    def __init__(self):
        super().__init__(0x0307)


# ------------------------------------------------------------
# fourbytes
# ------------------------------------------------------------

class m0536(fourbytes):
    def __init__(self):
        super().__init__(0x0536)


# ------------------------------------------------------------
# nbytes
# ------------------------------------------------------------

class m0008(nbytes):
    def __init__(self):
        super().__init__(0x0008, hexparse('00 00 00 00 00 00 00 00'))


# ------------------------------------------------------------
# stringenums
# ------------------------------------------------------------

class m0013(stringenum):
    def __init__(self):
        super().__init__(0x0013)


# ------------------------------------------------------------
# arrayofenumblockarrays
# ------------------------------------------------------------

class m00e9(arrayofenumblockarrays):
    def __init__(self):
        super().__init__(0x00e9)

    def setservers(self, servers, player_address):
        self.arrays = []
        for server in servers:
            if not server.joinable:
                continue

            self.arrays.append([
                m0385(),
                m06ee(),
                m02c7().set(server.server_id),
                m0008(),
                m02ff(),
                m02ed(),
                m02d8(),
                m02ec(),
                m02d7(),
                m02af(),
                m0013(),
                m00aa(),
                m01a6(),
                m06f1(),
                m0703(),
                m0343().set(len(server.players)),
                m0344(),
                m0259(),
                m03fd(),
                m02b3(),
                m0448().set(server.region),
                m02d6(),
                m06f5(),
                m0299(),
                m0298(),
                m06bf(),
                m069c().set(0x01 if server.password_hash is not None else 0x00),
                m069b().set(0x01 if server.password_hash is not None else 0x00),
                m0300().set(server.game_setting_mode.upper() + ' | ' + server.description),
                m01a4().set(server.motd),
                m02b2().set(server.map_id),
                m02b5(),
                m0347().set(0x00000018),
                m02f4().set(server.get_time_remaining()),
                m0035().set(server.be_score),
                m0197().set(server.ds_score),
                m0246().set(server.address_pair.get_address_seen_from(player_address), server.pingport)
                                                # The value doesn't matter, the client uses the address in a0035
            ])
        return self

    def setplayers(self, players):
        assert len(self.arrays) == 1, 'Can only set players for an m00e9 message that contains a single server'
        self.arrays[0].append(
            m0132().setplayers(players)
        )
        return self



# ------------------------------------------------------------
# enumblockarrays
# ------------------------------------------------------------

class a003b(enumblockarray):
    def __init__(self):
        super().__init__(0x003b)


# ------------------------------------------------------------
# special fields
# ------------------------------------------------------------

# Player password
class m0056(variablelengthbytes):
    def __init__(self):
        super().__init__(0x0056, b'0' * 90)

    def read(self, stream):
        super().read(stream)
        if len(self.content) < 72:
            raise ParseError('self.content is not allowed to be shorter than 72 bytes')
        return self


# Server password
class m032e(passwordlike):
    def __init__(self):
        super().__init__(0x032e, b'0')


class m0620(passwordlike):
    def __init__(self):
        super().__init__(0x0620, b'0')


class originalfragment():
    def __init__(self, fromoffset, tooffset):
        self.fromoffset = fromoffset
        self.tooffset = tooffset

    def write(self, stream):
        stream.write(_originalbytes(self.fromoffset, self.tooffset))


def construct_top_level_enumfield(stream):
    ident = struct.unpack('<H', stream.peek(2))[0]
    classname_a = ('a%04X' % ident).lower()
    classname_m = ('m%04X' % ident).lower()

    if classname_a not in globals():
        if classname_m not in globals():
            raise RuntimeError(f'Unable to parse enumfield {ident:04x}')
        else:
            messageclass = classname_m
    else:
        messageclass = classname_a

    obj = globals()[messageclass]().read(stream)
    return obj
