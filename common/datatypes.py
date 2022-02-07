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




class m0016(nbytes):
    def __init__(self):
        super().__init__(0x0016, hexparse('00 00 00'))
#

class m001c(fourbytes):
    def __init__(self):
        super().__init__(0x001c)
#

class m001f(fourbytes):
    def __init__(self):
        super().__init__(0x001f)
#

class m0020(stringenum):
    def __init__(self):
        super().__init__(0x0020, '')
#AgencyDescription

class m0023(stringenum):
    def __init__(self):
        super().__init__(0x0023, '')
#DailyMessage

class m0024(stringenum):
    def __init__(self):
        super().__init__(0x0024, '')
#AgencyName

class m0029(fourbytes):
    def __init__(self):
        super().__init__(0x0029)
#

class m002C(stringenum):
    def __init__(self):
        super().__init__(0x002C, '')
#AllianceName

class a0034(enumblockarray):
    def __init__(self):
        super().__init__(0x0034)
#

class a0036(enumblockarray):
    def __init__(self):
        super().__init__(0x0036)
#

class a0039(enumblockarray):
    def __init__(self):
        super().__init__(0x0039)
#

class a003b(enumblockarray):
    def __init__(self):
        super().__init__(0x003b)
#

class a003e(enumblockarray):
    def __init__(self):
        super().__init__(0x003e)
#

class a0042(enumblockarray):
    def __init__(self):
        super().__init__(0x0042)
#

class m005d(stringenum):
    def __init__(self):
        super().__init__(0x005d, '')
#

class m0064(nbytes):
    def __init__(self):
        super().__init__(0x0064, hexparse('00 00 00 00 00 00 00 00'))
#

class a0071(enumblockarray):
    def __init__(self):
        super().__init__(0x0071)
#

class a0071(enumblockarray):
    def __init__(self):
        super().__init__(0x0071)
#

class a0072(enumblockarray):
    def __init__(self):
        super().__init__(0x0072)
#

class a0073(enumblockarray):
    def __init__(self):
        super().__init__(0x0073)
#

class a0082(enumblockarray):
    def __init__(self):
        super().__init__(0x0082)
#

class a0088(enumblockarray):
    def __init__(self):
        super().__init__(0x0088)
#

class a008d(enumblockarray):
    def __init__(self):
        super().__init__(0x008d)
#

class m008d(onebyte):
    def __init__(self):
        super().__init__(0x008d)
#

class a008e(enumblockarray):
    def __init__(self):
        super().__init__(0x008e)
#

class m009b(fourbytes):
    def __init__(self):
        super().__init__(0x009b)
#

class m00b5(fourbytes):
    def __init__(self):
        super().__init__(0x00b5)
#Character ID or class

class m00bd(fourbytes):
    def __init__(self):
        super().__init__(0x00bd)
#

class m00be(fourbytes):
    def __init__(self):
        super().__init__(0x00be)
#

class m00bf(nbytes):
    def __init__(self):
        super().__init__(0x00bf, hexparse('00 00 00 00 00 00 00 00'))
#

class a00c2(enumblockarray):
    def __init__(self):
        super().__init__(0x00c2)
#

class m00c2(stringenum):
    def __init__(self):
        super().__init__(0x00c2, '')
#

class a00da(enumblockarray):
    def __init__(self):
        super().__init__(0x00da)
#

class m00db(fourbytes):
    def __init__(self):
        super().__init__(0x00db)
#

class m00e4(fourbytes):
    def __init__(self):
        super().__init__(0x00e4)
#

class m00f4(fourbytes):
    def __init__(self):
        super().__init__(0x00f4)
#

class m00f6(fourbytes):
    def __init__(self):
        super().__init__(0x00f6)
#

class m0104(twobytes):
    def __init__(self):
        super().__init__(0x0104)
#

class m010c(arrayofenumblockarrays):
    def __init__(self):
        super().__init__(0x010c)
#

class m0110(fourbytes):
    def __init__(self):
        super().__init__(0x0110)
#

class a0126(enumblockarray):
    def __init__(self):
        super().__init__(0x0126)
#

class m0136(arrayofenumblockarrays):
    def __init__(self):
        super().__init__(0x0136)
#

class a0144(enumblockarray):
    def __init__(self):
        super().__init__(0x0144)
#

class m0152(arrayofenumblockarrays):
    def __init__(self):
        super().__init__(0x0152)
#

class m0170(arrayofenumblockarrays):
    def __init__(self):
        super().__init__(0x0170)
#

class m0180(arrayofenumblockarrays):
    def __init__(self):
        super().__init__(0x0180)
#

class a0184(enumblockarray):
    def __init__(self):
        super().__init__(0x0184)
#

class a0188(enumblockarray):
    def __init__(self):
        super().__init__(0x0188)
#

class a01ae(enumblockarray):
    def __init__(self):
        super().__init__(0x01ae)
#

class a01bc(enumblockarray):
    def __init__(self):
        super().__init__(0x01bc)
#

class a01e8(enumblockarray):
    def __init__(self):
        super().__init__(0x01e8)
#

class m01f9(fourbytes):
    def __init__(self):
        super().__init__(0x01f9)
#

class m01ff(fourbytes):
    def __init__(self):
        super().__init__(0x01ff)
#

class a0200(enumblockarray):
    def __init__(self):
        super().__init__(0x0200)
#

class m0213(nbytes):
    def __init__(self):
        super().__init__(0x0213, hexparse('00 00 00'))
#

class m021c(fourbytes):
    def __init__(self):
        super().__init__(0x021c)
#

class m021c(fourbytes):
    def __init__(self):
        super().__init__(0x021c)
#

class m0231(fourbytes):
    def __init__(self):
        super().__init__(0x0231)
#

class m0235(fourbytes):
    def __init__(self):
        super().__init__(0x0235)
#

class m023f(fourbytes):
    def __init__(self):
        super().__init__(0x023f)
#item class

class m0241(fourbytes):
    def __init__(self):
        super().__init__(0x0241)
#

class m025d(fourbytes):
    def __init__(self):
        super().__init__(0x025d)
#

class m0262(fourbytes):
    def __init__(self):
        super().__init__(0x0262)
#

class m0264(fourbytes):
    def __init__(self):
        super().__init__(0x0264)
#

class m0270(fourbytes):
    def __init__(self):
        super().__init__(0x0270)
#

class m0276(fourbytes):
    def __init__(self):
        super().__init__(0x0276)
#gender

class m0282(fourbytes):
    def __init__(self):
        super().__init__(0x0282)
#PlayerHead?

class m0287(fourbytes):
    def __init__(self):
        super().__init__(0x0287)
#gender related?

class m02a9(fourbytes):
    def __init__(self):
        super().__init__(0x02a9)
#

class m02b1(stringenum):
    def __init__(self):
        super().__init__(0x02b1, '')
#

class m02b2(nbytes):
    def __init__(self):
        super().__init__(0x02b2, hexparse('00 00 00 00 00 00 00 00'))
#

class m02bf(fourbytes):
    def __init__(self):
        super().__init__(0x02bf)
#

class m02c1(stringenum):
    def __init__(self):
        super().__init__(0x02c1, '')
#

class m02c8(fourbytes):
    def __init__(self):
        super().__init__(0x02c8)
#

class m02c9(fourbytes):
    def __init__(self):
        super().__init__(0x02c9)
#

class m02ca(fourbytes):
    def __init__(self):
        super().__init__(0x02ca)
#

class m02cb(fourbytes):
    def __init__(self):
        super().__init__(0x02cb)
#

class m02da(fourbytes):
    def __init__(self):
        super().__init__(0x02da)
#item instance

class m02e0(fourbytes):
    def __init__(self):
        super().__init__(0x02e0)
#

class m02ff(nbytes):
    def __init__(self):
        super().__init__(0x02ff, hexparse('00 00 00 00 00 00 00 00'))
#

class m0303(fourbytes):
    def __init__(self):
        super().__init__(0x0303)
#

class m0315(fourbytes):
    def __init__(self):
        super().__init__(0x0315)
#

class m0319(fourbytes):
    def __init__(self):
        super().__init__(0x0319)
#

class m0321(stringenum):
    def __init__(self):
        super().__init__(0x0321, '')
#

class m0322(fourbytes):
    def __init__(self):
        super().__init__(0x0322)
#

class m0325(fourbytes):
    def __init__(self):
        super().__init__(0x0325)
#

class m0326(stringenum):
    def __init__(self):
        super().__init__(0x0326, '')
#Location

class m0327(fourbytes):
    def __init__(self):
        super().__init__(0x0327)
#

class m0330(fourbytes):
    def __init__(self):
        super().__init__(0x0330)
#

class m0347(fourbytes):
    def __init__(self):
        super().__init__(0x0347)
#

class m0355(stringenum):
    def __init__(self):
        super().__init__(0x0355, '')
#message

class m0360(stringenum):
    def __init__(self):
        super().__init__(0x0360, '')
#

class m0365(fourbytes):
    def __init__(self):
        super().__init__(0x0365)
#PlayerHead?

class m0366(fourbytes):
    def __init__(self):
        super().__init__(0x0366)
#

class m036e(fourbytes):
    def __init__(self):
        super().__init__(0x036e)
#

class m0370(stringenum):
    def __init__(self):
        super().__init__(0x0370, '')
#sender

class m0371(fourbytes):
    def __init__(self):
        super().__init__(0x0371)
#

class m0375(twobytes):
    def __init__(self):
        super().__init__(0x0375)
#

class m0376(fourbytes):
    def __init__(self):
        super().__init__(0x0376)
#

class m0379(onebyte):
    def __init__(self):
        super().__init__(0x0379)
#

class m037a(stringenum):
    def __init__(self):
        super().__init__(0x037a, '')
#

class m0388(onebyte):
    def __init__(self):
        super().__init__(0x0388)
#

class m0395(fourbytes):
    def __init__(self):
        super().__init__(0x0395)
#

class m039f(twobytes):
    def __init__(self):
        super().__init__(0x039f)
#

class m03a5(fourbytes):
    def __init__(self):
        super().__init__(0x03a5)
#

class m03a8(twobytes):
    def __init__(self):
        super().__init__(0x03a8)
#

class m03c0(fourbytes):
    def __init__(self):
        super().__init__(0x03c0)
#

class m03c1(fourbytes):
    def __init__(self):
        super().__init__(0x03c1)
#

class m03c2(fourbytes):
    def __init__(self):
        super().__init__(0x03c2)
#

class m03c3(fourbytes):
    def __init__(self):
        super().__init__(0x03c3)
#

class m03c5(stringenum):
    def __init__(self):
        super().__init__(0x03c5, '')
#PlayerName/receiver

class m03d6(fourbytes):
    def __init__(self):
        super().__init__(0x03d6)
#

class m03df(fourbytes):
    def __init__(self):
        super().__init__(0x03df)
#CharClass

class m03fd(fourbytes):
    def __init__(self):
        super().__init__(0x03fd)
#

class m03fe(fourbytes):
    def __init__(self):
        super().__init__(0x03fe)
#

class m041e(fourbytes):
    def __init__(self):
        super().__init__(0x041e)
#

class m041f(stringenum):
    def __init__(self):
        super().__init__(0x041f, '')
#RecruitmentMessage

class m044c(fourbytes):
    def __init__(self):
        super().__init__(0x044c)
#

class m046f(fourbytes):
    def __init__(self):
        super().__init__(0x046f)
#

class m046f(fourbytes):
    def __init__(self):
        super().__init__(0x046f)
#

class m0480(fourbytes):
    def __init__(self):
        super().__init__(0x0480)
#

class m0485(fourbytes):
    def __init__(self):
        super().__init__(0x0485)
#

class m0489(fourbytes):
    def __init__(self):
        super().__init__(0x0489)
#

class m048e(fourbytes):
    def __init__(self):
        super().__init__(0x048e)
#

class m049e(fourbytes):
    def __init__(self):
        super().__init__(0x049e)
#

class m04bf(fourbytes):
    def __init__(self):
        super().__init__(0x04bf)
#

class m04c0(fourbytes):
    def __init__(self):
        super().__init__(0x04c0)
#

class m04c5(nbytes):
    def __init__(self):
        super().__init__(0x04c5, hexparse('00 00 00 00 00 00 00 00'))
#

class m04d4(onebyte):
    def __init__(self):
        super().__init__(0x04d4)
#

class m04da(fourbytes):
    def __init__(self):
        super().__init__(0x04da)
#

class m04e4(fourbytes):
    def __init__(self):
        super().__init__(0x04e4)
#

class m04e7(fourbytes):
    def __init__(self):
        super().__init__(0x04e7)
#

class m04ff(stringenum):
    def __init__(self):
        super().__init__(0x04ff, '')
#

class m0515(fourbytes):
    def __init__(self):
        super().__init__(0x0515)
#

class m052d(stringenum):
    def __init__(self):
        super().__init__(0x052d, '')
#

class m0531(stringenum):
    def __init__(self):
        super().__init__(0x0531, '')
#

class m0536(fourbytes):
    def __init__(self):
        super().__init__(0x0536)
#

class m053d(fourbytes):
    def __init__(self):
        super().__init__(0x053d)
#

class m053e(fourbytes):
    def __init__(self):
        super().__init__(0x053e)
#

class m0541(fourbytes):
    def __init__(self):
        super().__init__(0x0541)
#

class m0542(fourbytes):
    def __init__(self):
        super().__init__(0x0542)
#

class m0552(fourbytes):
    def __init__(self):
        super().__init__(0x0552)
#

class m0563(fourbytes):
    def __init__(self):
        super().__init__(0x0563)
#Level (xp) false? changes every login

class m0572(fourbytes):
    def __init__(self):
        super().__init__(0x0572)
#

class m0598(onebyte):
    def __init__(self):
        super().__init__(0x0598)
#

class m05c3(fourbytes):
    def __init__(self):
        super().__init__(0x05c3)
#

class m05d1(onebyte):
    def __init__(self):
        super().__init__(0x05d1)
#

class m05f4(arrayofenumblockarrays):
    def __init__(self):
        super().__init__(0x05f4)
#

class m05f5(fourbytes):
    def __init__(self):
        super().__init__(0x05f5)
#

class m05f6(fourbytes):
    def __init__(self):
        super().__init__(0x05f6)
#

class m05f7(fourbytes):
    def __init__(self):
        super().__init__(0x05f7)
#

class m0609(fourbytes):
    def __init__(self):
        super().__init__(0x0609)
#

class m060a(fourbytes):
    def __init__(self):
        super().__init__(0x060a)
#




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
