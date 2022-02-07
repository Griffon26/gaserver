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

from common.datatypes import *
from .authenticated_state import AuthenticatedState
from ..state.player_state import PlayerState, handles


def choose_display_name(login_name, verified, names_in_use, max_name_length):
    if verified:
        display_name = login_name[:max_name_length]
    else:
        prefix = 'unvrf-'
        display_name = prefix + login_name[:max_name_length - len(prefix)]
        index = 2
        lowercase_names_in_use = [name.lower() for name in names_in_use]
        while display_name.lower() in lowercase_names_in_use:
            display_name = 'unv%02d-%s' % (index, login_name[:max_name_length - len(prefix)])
            index += 1
            assert index < 100

    return display_name


class UnauthenticatedState(PlayerState):
    def on_enter(self):
        self.logger.info("%s is entering state %s" % (self.player, type(self).__name__))
        self.player.start_idle_timeout()

    @handles(packet=a003b)
    def handle_login_request(self, request):
        if request.findbytype(m0071) is None:  # request for login
            self.player.send(a003b().set([
                m0536().set(0x01050001),
                m0473()
            ]))

        else:  # actual login
            self.player.login_name = request.findbytype(m052d).value
            self.player.password_hash = request.findbytype(m0071).content

            validation_failure = self.player.login_server.validate_username(self.player.login_name)
            if validation_failure:
                self.player.send([
                    a003d().set([
                        m0442().set_success(False),
                        m02fc().set(STDMSG_LOGIN_INFO_INVALID),
                        m0219(),
                        m0019(),
                        m0623(),
                        m05d6(),
                        m03e3(),
                        m00ba()
                    ])
                ])
                self.logger.info("Rejected login attempt with user name %s: %s" %
                                 (self.player.login_name.encode('latin1'), validation_failure))

            else:
                names_in_use = [p.display_name for p in self.player.login_server.players.values()
                                if p.display_name is not None]
                self.player.display_name = choose_display_name(self.player.login_name,
                                                               self.player.verified,
                                                               names_in_use,
                                                               self.player.max_name_length)
                self.player.send([
                    a003e().set([
                        m03c3().set(0x0017e6d5),
                        m0375().set(0xf3f8),
                        m01ff(),
                        m0213().set(hexparse('01 00 6e')),
                        m03c5().set(self.player.display_name),
                        m04d4().set(1),
                        m036e().set(0x4949),
                        m0064(),
                        m0473(),
                        m00db().set(0x8bcc),
                        m0270().set(0xf),
                        m001c().set(0x384),
                        m04ff().set("pageup"),
                        m010c().set([
                            [
                                m04da().set(1),
                                m0371().set(0xa26f),
                            ],
                            [
                                m04da().set(2),
                                m0371().set(0xa20b),
                            ],
                            [
                                m04da().set(4),
                                m0371().set(0xcfac),
                            ]
                        ])

                    ]),
                    m0170().set([
                        [
                            m0322().set(0x46b),
                            m0262().set(0xab95),
                        ],
                    ])
                ])
                self.player.set_state(AuthenticatedState)
