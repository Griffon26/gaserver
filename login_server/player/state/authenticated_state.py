#!/usr/bin/env python3
#
# Copyright (C) 2018  Maurice van der Pot <griffon26@kfk4ever.com>,
# Copyright (C) 2018 Timo Pomer <timopomer@gmail.com>
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

import datetime

from common.datatypes import *
from .player_state import PlayerState, handles, handles_control_message
from common import utils


class AuthenticatedState(PlayerState):

    def on_enter(self):
        self.logger.info("%s is entering state %s" % (self.player, type(self).__name__))
        self.player.friends.notify_online()

    def on_exit(self):
        self.logger.info("%s is exiting state %s" % (self.player, type(self).__name__))

    #@handles(packet=a00d5)
    #def handle_a00d5(self, request):
    #    if request.findbytype(m0228).value == 1:
    #        self.player.send(originalfragment(0x1EEB3, 0x20A10))  # 00d5 (map list)
    #    else:
    #        self.player.send(a00d5().setservers(self.player.login_server
    #                                            .all_game_servers()
    #                                            .values(),
    #                                            self.player.address_pair))  # 00d5 (server list)

