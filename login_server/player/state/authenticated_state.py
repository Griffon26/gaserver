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
