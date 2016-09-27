from enum import Enum, unique
import random

import transitions


@unique
class Card(Enum):
    """Card."""
    INFANTRY = 1
    CAVALRY = 2
    ARTILLERY = 3


class Redeem(Enum):
    """Redeem three Cards for bonus troops."""
    INFANTRY  = ([Card.INFANTRY]  * 3, 4)
    CAVALRY   = ([Card.CAVALRY]   * 3, 6)
    ARTILLERY = ([Card.ARTILLERY] * 3, 8)
    MIXED = ([Card.INFANTRY, Card.CAVALRY, Card.ARTILLERY], 10)


class Player(object):
    """Wrap a player identifier with additional information
        used during a game."""
    def __init__(self, ident):
        self.ident = ident
        self.owned_countries = 0
        # used to check if player may draw a card
        self.conquered_country_in_turn = False
        # troops the player may deploy in this turn
        self.available_troops = 0
        # player's bonus cards
        self.cards = []

    def __eq__(self, other):
        return self.ident == other.ident

    def __ne__(self, other):
        return self.ident != other.ident

    def __hash__(self):
        return hash(self.ident)


class Action(object):
    def __init__(self, board):
        self.board = board

    def prepare(self, message):
        self.current_message = message

    def is_permitted(self, _):
        return True

    def execute(self, _):
        pass

    def next_turn(self, player):
        self.current_player = player

    def answer(self, message, player=None):
        if player is None:
            player = self.current_player

        self.current_message.add_answer(player, message)


class BonusAction(Action):
    def prepare(self, message):
        super().prepare(message)
        self.redeem = None  # TODO

    def is_permitted(self, _):
        player_cards = self.current_player.cards.copy()
        redeem_cards, _ = self.redeem.value

        # check if player has every card needed to redeem what he claims
        for card in redeem_cards:
            try:
                player_cards.remove(card)
            except ValueError:
                # player wants to redeem card but does not have it
                return False

        # player has all cards
        return True

    def execute(self, _):
        player = self.current_player
        player_cards = player.cards

        redeem_cards, value = self.redeem.value
        player.available_troops += value

        for card in redeem_cards:
            player_cards.remove(card)

        self.answer(Redeemed(redeem))


class DeployAction(Action):
    def prepare(self, message):
        super().prepare(message)
        self.country = self.board.country_for_name(message.country)
        self.troops = message.troops

    def is_permitted(self, _):
        return (self.current_player == self.country.owner
                and self.current_player.available_troops >= self.troops)

    def execute(self, _):
        self.country.troops += self.troops
        self.current_player.available_troops -= self.troops

        self.answer(Deployed(self.country, self.troops))


class AttackAction(Action):
    def prepare(self, message):
        super().prepare(message)
        self.origin = self.board.country_for_name(message.origin)
        self.destination = self.board.country_for_name(message.destination)
        self.attack_troops = message.attack_troops


    def is_permitted(self, _):
        return (self._current_player_is_owner(self.origin)
                and not self._current_player_is_owner(self.destination)
                and self.origin.troops > self.attack_troops  # one troop must remain
                and self.attack_troops >= 1
                and self.attack_troops <= 3)

    def _current_player_is_owner(self, country):
        return self.current_player == country.owner

    def execute(self, _):
        attacker = self.current_player
        defender = self.destination.owner

        attack_troops = self.attack_troops
        defend_troops = min(self.attack_troops, self.destination.troops, 2)

        attack_dice = self._roll_dice(attack_troops)
        defend_dice = self._roll_dice(defend_troops)

        attack_losses = 0
        defend_losses = 0
        for (a, d) in zip(attack_dice, defend_dice):
            if a > d:  # attacker won
                defend_losses += 1
            else:  # defender won
                attack_losses += 1

        self.origin.troops -= attack_losses
        self.destination.troops -= defend_losses

        if self.destination.troops == 0:
            # defending country is conquered
            attacker.owned_countries += 1
            defender.owned_countries -= 1

            self.destination.troops = attack_troops
            self.destination.owner = attacker

            attacker.conquered_country_in_turn = True

            self.answer(attacker, Conquered(destination))
            self.answer(defender, Defeated(destination))
        else:
            self.answer(attacker, Attacked(destination, attack_losses))
            self.answer(defender, Defended(destination, defend_losses))

    @staticmethod
    def _roll_dice(n):
        return [random.randint(1, 6) for _ in range(n)].sort(reverse=True)


class MoveAction(Action):
    def prepare(self, message):
        super().prepare(message)
        self.origin = self.board.country_for_name(message.origin)
        self.destination = self.board.country_for_name(message.destination)
        self.troops = message.troops

    def is_permitted(self, _):
        return (self._current_player_is_owner(self.origin)
                and self._current_player_is_owner(self.destination)
                and self.origin.troops > self.troops)  # at least one troop must remain
                # TODO: do countries have to be neighbours/ connected?

    def _current_player_is_owner(self, country):
        return self.current_player == country.owner

    def execute(self, _):
        self.origin.troops -= self.troops
        self.destination.troops += self.troops
        self.current_player.notify(Moved(origin, destination, troops))


class GetCardAction(Action):
    def is_permitted(self, _):
        return self.current_player.conquered_country_in_turn

    def execute(self, _):
        new_card = random.choice(list(Card))
        self.current_player.cards.append(new_card)
        self.current_player.notify(GotCard(new_card))


class NextTurnAction(Action):
    def __init__(self, board, players, actions):
        super().__init__(board)
        # contains all players except the current one
        self.players = players[1:]
        # player whose turn it is now
        self.current_player = players[0]
        self.actions = actions

    def next_turn(self):
        pass

    def execute(self):
        # rotate list with current player
        self.players.append(self.current_player)
        self.current_player = players[0]
        self.players = self.players[1:]

        # TODO: probably more logic to set up the next player's turn
        player = self.current_player
        player.conquered_country_in_turn = False
        player.available_troops = player.available_troops // 3

        for action in self.actions:
            actions.next_turn(player)


class Logic(object):
    """Implements the Logic for a game of Risk"""
    def __init__(self, board, players):
        self.board = board

        self.players = []
        for ident in players:
            self.players.append(Player(ident))

        self.distribute_countries()

        # State machine that checks if an action is
        # allowed for the current player right now
        # and if so performs the action.
        before_start = 'before_start'  # before the first move
        start_of_turn = 'start_of_turn'  # at the start of a player's turn
        got_bonus = 'got_bonus'  # player redeem a bonus
        deploying = 'deploying'  # player is deploying troops
        attacking = 'attacking'  # player is attacking others
        drew_card = 'drew_card'  # player drew a card after attacking
        moved = 'moved'  # player moved troops

        redeem = BonusAction(board)
        deploy = DeployAction(board)
        attack = AttackAction(board)
        get_card = GetCardAction(board)
        move = MoveAction(board)

        actions = [redeem, deploy, attack, get_card, move]
        next_turn = NextTurnAction(board, players, actions)


        states = [before_start, start_of_turn, got_bonus, deploying, attacking, moved, drew_card]

        def make_transition(trigger, source, dest, action):
            return {
                'trigger': trigger,
                'source': source,
                'dest': dest,
                'prepare': action.prepare,
                'conditions': action.is_permitted,
                'after': action.execute,
            }

        trans = [
            make_transition('redeem', start_of_turn, got_bonus, redeem),
            make_transition('deploy',
                [start_of_turn, got_bonus, deploying], deploying, deploy),
            make_transition('attack', [deploying, attacking], attacking, attack),
            make_transition('draw_card', attacking, drew_card, get_card),
            make_transition('move',
                [deploying, attacking, drew_card], moved, move),
            make_transition('next_turn',
                [before_start, deploying, attacking, drew_card, moved],
                start_of_turn, next_turn)
        ]

        self.machine = transitions.Machine(
            self,
            states=states,
            transitions=trans,
            initial=before_start,
            auto_transitions=False
        )

    def distribute_countries(self):
        # TODO: is this a fair distribution?
        num_players = len(self.players)
        countries = self.board.countries()
        random.shuffle(countries)

        for i, country in enumerate(countries):
            player = self.players[i % num_players]
            country.owner = player
            player.owned_countries += 1


    def is_ingame(self, player):
        # TODO: fails if player is not instanceof(Player)
        return player in self.players

    def kick(self, player):
        # TODO: remove player from game, board, etc.
        print('kick idiot', player)
