#!/usr/bin/env python3
#
# Copyright (C) 2018-2019  Maurice van der Pot <griffon26@kfk4ever.com>
#
# This file is part of gaserver
#
# gaserver is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# gaserver is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with gaserver.  If not, see <http://www.gnu.org/licenses/>.
#

import io
import struct

from common.connectionhandler import *
from .datatypes import construct_top_level_enumfield


def peekshort(infile):
    values = infile.peek(2)
    if len(values) == 0:
        raise EOFError
    return struct.unpack('H', values)[0]


def readlong(infile):
    values = infile.read(4)
    if len(values) == 0:
        raise EOFError
    return struct.unpack('<L', values)[0]


def parseseqack(infile):
    seq = readlong(infile)
    ack = readlong(infile)
    return seq, ack


class PacketReader:
    def __init__(self, receive_func):
        self.buffer = bytes()
        self.receive_func = receive_func

    def prepare(self, length):
        ''' Makes sure that at least length bytes are available in self.buffer '''
        while len(self.buffer) < length:
            message_data = self.receive_func()
            self.buffer += message_data

    def read(self, length):
        self.prepare(length)
        requestedbytes = self.buffer[:length]
        self.buffer = self.buffer[length:]
        return requestedbytes

    def peek(self, length):
        self.prepare(length)
        requestedbytes = self.buffer[:length]
        return requestedbytes

    def tell(self):
        return 0


class StreamParser:
    def __init__(self, in_stream):
        self.in_stream = in_stream

    def parse(self):
        return [construct_top_level_enumfield(self.in_stream)]


class LoginProtocolMessage:
    def __init__(self, requests):
        self.requests = requests


class LoginProtocolReader(TcpMessageConnectionReader):
    def __init__(self, sock, dump_queue):
        super().__init__(sock, max_message_size = 1450, dump_queue = dump_queue)
        packet_reader = PacketReader(super().receive)
        self.stream_parser = StreamParser(packet_reader)

    def receive(self):
        return None

    def decode(self, msg_bytes):
        msg = self.stream_parser.parse()
        return LoginProtocolMessage(msg)


class LoginProtocolWriter(TcpMessageConnectionWriter):
    def __init__(self, sock, dump_queue):
        super().__init__(sock, max_message_size = 1450, dump_queue = dump_queue)

    def encode(self, message):
        stream = io.BytesIO()

        if isinstance(message, list):
            for el in message:
                el.write(stream)
        else:
            message.write(stream)

        return stream.getvalue()
