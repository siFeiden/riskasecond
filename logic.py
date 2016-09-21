import random


class Logic(object):
    """Implements the Logic for a game of Risk"""
    def __init__(self, board, players):
        self.board = board
        self.players = players

    def distribute_countries(self):
        num_players = len(self.players)
        countries = self.board.countries()
        random.shuffle(countries)

        for i, country in enumerate(countries):
            country.owner = self.players[i % num_players]

    def is_ingame(self, player):
        return player in self.players

    def kick(self, player):
        print('kick idiot', player)
