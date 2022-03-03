#!/usr/bin/env python3
#
# Copyright (C) 2018  Maurice van der Pot <griffon26@kfk4ever.com>,
# Copyright (C) 2018 Timo Pomer <timopomer@gmail.com>
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

import datetime

from common.datatypes import *
from .player_state import PlayerState, handles, handles_control_message
from common import utils


class AuthenticatedState(PlayerState):

    def on_enter(self):
        self.logger.info("%s is entering state %s" % (self.player, type(self).__name__))

    def on_exit(self):
        self.logger.info("%s is exiting state %s" % (self.player, type(self).__name__))

    @handles(packet=a0034)
    def handle_a0034(self, request):
        self.player.send(a0034().set([
            m03c5().set(self.player.display_name),
            m010c().set([
                [
                    m00b5().set(0x2ac950),
                    m03df().set(0x237),
                    m0287().set(0x645),
                    m0282().set(0x85d),
                    m0276().set(0x355),
                    m0326().set("Dome City"),
                    m0563().set(0x1f4),
                    m0480().set(0xb),
                ],
            ]),
            m0180(),
            m0136()
        ]))

    @handles(packet=a0039)
    def handle_a0039(self, request):
        self.player.send(a0039().set([
            m0241(),
            m02a9().set(0x00000497),
            m00b5().set(0x002ac950),
            m03c5().set(self.player.display_name),
            m0327(),
            m03df().set(0x00000237),
            m00c2().set("22976"),
            m0303(),
            m0485(),
            m001f(),
            m0029(),
            m0388(),
            m00bf().set(hexparse('02 00 23 29 7f 00 00 01')),
        ]))

    @handles(packet=a01e8)
    def handle_a01e8(self, request):
        self.player.send(a01e8().set([
            #m04da().set(0x2), #or m05d1().set(0x1) how to handle ambiguous..?
            m04da().set(0x2),
            m05d1().set(0x1),
        ]))

    @handles(packet=a0188)
    def handle_a0188(self, request):
        self.player.send(a0188().set([
            m0376(),
        ]))

'''
0000009E`  0  : enumfield 01E8 enumblockarray length 1 (field 0x01E8: DEFEND_ALLIANCE_ID?)
000000A2`      0  : enumfield 04DA 00000002 (field 0x04DA: SYS_SITE_ID)

000000A8`  0  : enumfield 01E8 enumblockarray length 1 (field 0x01E8: DEFEND_ALLIANCE_ID?)
000000AC`      0  : enumfield 05D1 01 (field 0x05D1: SYS_AVA_TEAMS_OK)



000000EA`  0  : enumfield 0188 enumblockarray length 0 (field 0x0188: DATA_SET_PRODUCTION_FLAIRS)

0000390C`  0  : enumfield 0188 enumblockarray length 1 (field 0x0188: DATA_SET_PRODUCTION_FLAIRS)
    00003910`      0  : enumfield 0376 00000000 (field 0x0376: NEW_MAIL_COUNT)
'''