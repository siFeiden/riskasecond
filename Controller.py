import asyncio as aio
from board  import Board
from link   import *
from logic  import Logic
from server import Server

class Controller(Server.Callbacks):
  """The Controller glues together all functionality."""

  PLAYERS_PER_GAME = 4

  def __init__(self):
    self.board = None
    self.logic = None

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
    players.shuffle()
    chosen_players = players[:Controller.PLAYERS_PER_GAME]

    self.logic = Logic(board, chosen_players)

    # TODO: notify players about game

  async def player_connected(self, player):
    print("New player: ", player)
    self.available_players.add(player)

    if len(self.available_players) == Controller.PLAYERS_PER_GAME:
      self.start_game()

  async def player_disconnected(self, player):
    print("Lost player: ", player)
    self.available_players.remove(id)

    if self.logic and self.logic.is_ingame(player):
      self.logic.kick(player)

  async def message(self, player, payload):
    try:
      msg_type, message = self.message_parser.parse(payload)
      self.dispatch_message(player, msg_type, message)
    except ParseError:
      print('parsing failed: ', payload)
      if self.logic and self.logic.is_ingame(player):
        self.logic.kick(player)

  def dispatch_message(self, player, message_type, payload):
    if message_type == Message.Type.Echo:
      print('Echo message:', payload)
      self.server.send_message(player, payload)
    else:
      print('Unknown message type', message_type)


if __name__ == '__main__':
  Controller().main()