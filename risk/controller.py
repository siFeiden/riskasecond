import asyncio as aio
import random

from .board import Board
from .messages import Message, MessageParser, ParseError
from .logic import Logic
from .server import Server
from statemachine import MachineError


class Controller(Server.Callbacks):
    """The Controller glues together all functionality."""

    PLAYERS_PER_GAME = 4

    def __init__(self):
        self.board = Board()
        self.logic = Logic(self.board, ['a', 'b', 'c', 'd'])

        self.message_parser = MessageParser()
        self.available_players = set()

        self.loop = aio.get_event_loop()
        self.server = Server(self, self.loop)

    def main(self):
        self.server.run('localhost', 8000)

        try:
            self.loop.run_forever()
        finally:
            self.loop.close()

    def start_game(self):
        self.board = Board()

        players = list(self.available_players)
        random.shuffle(players)
        chosen_players = players[:Controller.PLAYERS_PER_GAME]

        self.logic = Logic(self.board, chosen_players)

        # TODO: notify players about game

    async def player_connected(self, player):
        print("New player: ", player)
        self.available_players.add(player)

        if len(self.available_players) == Controller.PLAYERS_PER_GAME:
            self.start_game()

    async def player_disconnected(self, player):
        print("Lost player: ", player)
        self.available_players.remove(player)

        if self.logic and self.logic.is_ingame(player):
            self.logic.kick(player)

    async def message(self, player, payload):
        try:
            message = self.message_parser.parse(payload)
            self.dispatch_message(player, message)
        except ParseError:
            print('parsing failed: ', payload)
            if self.logic and self.logic.is_ingame(player):
                self.logic.kick(player)

    def dispatch_message(self, player, message):
        tpe = message.type

        try:
            success = None

            if tpe == Message.Type.Echo:
                # do nothing
                success = True
            elif tpe == Message.Type.Deploy:
                success = self.logic.deploy(message)
            elif tpe == Message.Type.Attack:
                success = self.logic.attack(message)
            elif tpe == Message.Type.Move:
                success = self.logic.move(message)
            elif tpe == Message.Type.Card:
                success = self.logic.draw_card(message)
            elif tpe == Message.Type.Bonus:
                success = self.logic.bonus(message)
            else:
                msg = 'Unknown message type.'
                print(msg, message.type)

            if not success:
                msg = 'Preconditions for state change not fulfilled.'
                raise MachineError(msg)
        except MachineError:
            self.logic.kick(player)
        else:
            if message.success:
                self.server.send_message(player, message)

            for (recipient, answer) in message.answers:
                self.server.send_message(recipient, answer)


if __name__ == '__main__':
    Controller().main()
