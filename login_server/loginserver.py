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

import gevent
import datetime
import hashlib
import logging

from common.connectionhandler import PeerConnectedMessage, PeerDisconnectedMessage
from common.datatypes import *
from common.ipaddresspair import IPAddressPair
from common.loginprotocol import LoginProtocolMessage
#from common.messages import *
from common.statetracer import statetracer, TracingDict
#from .gameserver import GameServer
from common.pendingcallbacks import PendingCallbacks, ExecuteCallbackMessage
from .player.player import Player
from .player.state.offline_state import OfflineState
from .player.state.unauthenticated_state import UnauthenticatedState
from .protocol_errors import ProtocolViolationError
from common import utils


@statetracer('address_pair', 'game_servers', 'players')
class LoginServer:
    def __init__(self, server_queue, client_queues, server_stats_queue, ports):
        self.logger = logging.getLogger(__name__)
        self.server_queue = server_queue
        self.client_queues = client_queues
        self.server_stats_queue = server_stats_queue

        self.game_servers = TracingDict()

        self.players = TracingDict()
        self.message_handlers = {
            ExecuteCallbackMessage: self.handle_execute_callback_message,
            PeerConnectedMessage: self.handle_client_connected_message,
            PeerDisconnectedMessage: self.handle_client_disconnected_message,
            LoginProtocolMessage: self.handle_client_message,
        }
        self.pending_callbacks = PendingCallbacks(server_queue)
        self.last_player_update_time = datetime.datetime.utcnow()

        self.address_pair, errormsg = IPAddressPair.detect()
        if not self.address_pair.external_ip:
            self.logger.warning('Unable to detect public IP address: %s\n'
                                'This will cause problems if the login server '
                                'and any players are on the same LAN, but the '
                                'game server is not.' % errormsg)
        else:
            self.logger.info('detected external IP: %s' % self.address_pair.external_ip)

    def run(self):
        gevent.getcurrent().name = 'loginserver'
        self.logger.info('login server started')
        while True:
            for message in self.server_queue:
                handler = self.message_handlers[type(message)]
                try:
                    handler(message)
                except Exception as e:
                    if hasattr(message, 'peer'):
                        self.logger.error('an exception occurred while handling a message; passing it on to the peer...')
                        message.peer.disconnect(e)
                    else:
                        raise

    def all_game_servers(self):
        return self.game_servers

    def find_server_by_id(self, server_id):
        for game_server in self.all_game_servers().values():
            if game_server.server_id == server_id:
                return game_server
        raise ProtocolViolationError('No server found with specified server ID')

    def find_server_by_match_id(self, match_id):
        for game_server in self.all_game_servers().values():
            if game_server.match_id == match_id:
                return game_server
        raise ProtocolViolationError('No server found with specified match ID')

    def find_player_by(self, **kwargs):
        matching_players = self.find_players_by(**kwargs)

        if len(matching_players) > 1:
            raise ValueError("More than one player matched query")

        return matching_players[0] if matching_players else None

    def find_players_by(self, **kwargs):
        matching_players = self.players.values()
        for key, val in kwargs.items():
            matching_players = [player for player in matching_players if getattr(player, key) == val]

        return matching_players

    def find_player_by_display_name(self, display_name):
        matching_players = [p for p in self.players.values()
                            if p.display_name is not None and p.display_name.lower() == display_name.lower()]
        if matching_players:
            return matching_players[0]
        else:
            return None

    def change_player_unique_id(self, old_id, new_id):
        if new_id in self.players:
            raise AlreadyLoggedInError()

        assert old_id in self.players
        assert new_id not in self.players

        player = self.players.pop(old_id)
        player.unique_id = new_id
        self.players[new_id] = player

    def validate_username(self, username):
        if len(username) < Player.min_name_length:
            return 'User name is too short, min length is %d characters.' % Player.min_name_length

        if len(username) > Player.max_name_length:
            return 'User name is too long, max length is %d characters.' % Player.max_name_length

        try:
            ascii_bytes = username.encode('ascii')
        except UnicodeError:
            return 'User name contains invalid (i.e. non-ascii) characters'

        if not utils.is_valid_ascii_for_name(ascii_bytes):
            return 'User name contains invalid characters'

        if username.lower() == 'taserverbot':
            return 'User name is reserved'

        return None

    def send_server_stats(self):
        stats = [
            {'locked':      gs.password_hash is not None,
             'mode':        gs.game_setting_mode,
             'description': gs.description,
             'nplayers':    len(gs.players)} for gs in self.game_servers.values() if gs.joinable
        ]
        self.server_stats_queue.put(stats)

    def email_address_to_hash(self, email_address):
        email_hash = hashlib.sha256(email_address.encode('utf-8')).hexdigest()
        return email_hash

    def handle_execute_callback_message(self, msg):
        callback_id = msg.callback_id
        self.pending_callbacks.execute(callback_id)

    def handle_client_connected_message(self, msg):
        if isinstance(msg.peer, Player):
            unique_id = utils.first_unused_number_above(self.players.keys(),
                                                        utils.MIN_UNVERIFIED_ID,
                                                        utils.MAX_UNVERIFIED_ID)

            player = msg.peer
            player.unique_id = unique_id
            player.login_server = self
            player.complement_address_pair(self.address_pair)
            player.set_state(UnauthenticatedState)
            self.players[unique_id] = player
        else:
            assert False, "Invalid connection message received"

    def handle_client_disconnected_message(self, msg):
        if isinstance(msg.peer, Player):
            player = msg.peer
            player.disconnect()
            self.pending_callbacks.remove_receiver(player)
            player.set_state(OfflineState)
            del(self.players[player.unique_id])
        else:
            assert False, "Invalid disconnection message received"

    def handle_client_message(self, msg):
        current_player = msg.peer

        for request in msg.requests:
            if not current_player.handle_request(request):
                self.logger.info('%s sent: %04X' % (current_player, request.ident))

        # This output is mostly for debugging of the incorrect number of players/servers online
        current_time = datetime.datetime.utcnow()
        if int((current_time - self.last_player_update_time).total_seconds()) > 15 * 60:
            self.logger.info('currently online players:\n%s' % '\n'.join([f'    {p}' for p in self.players.values()]))
            self.logger.info('currently online servers:\n%s' % '\n'.join([f'    {s}' for s in self.game_servers.values()]))
            self.last_player_update_time = current_time
