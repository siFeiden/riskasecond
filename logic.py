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
    def __init__(self, ident, send_message):
        self.ident = ident
        self.owned_countries = 0
        # used to check if player may draw a card
        self.conquered_country_in_turn = False
        # troops the player may deploy in this turn
        self.available_troops = 0
        # player's bonus cards
        self.cards = []
        # send_message :: PlayerId -> Message -> ()
        # async. sends a message to a player
        self._send_message = send_message

    def notify(self, message):
        self._send_message(self.ident, message)

    def __eq__(self, other):
        return self.ident == other.ident

    def __ne__(self, other):
        return self.ident != other.ident

    def __hash__(self):
        return hash(self.ident)


class Logic(object):
    """Implements the Logic for a game of Risk"""
    def __init__(self, board, players, send_message):
        # send_message :: PlayerId -> Message -> ()
        # async. sends a message to a player

        self.board = board

        self.players = []
        for ident in players:
            self.players.apend(Player(ident, send_message))
        # player whose turn it is now
        self.current_player = self.players[0]
        # contains all players except the current one
        self.players = self.players[1:]

        # State machine that checks if an action is
        # allowed for the current player right now
        # and if so performs the action.
        initial = 'initial'
        redeem  = 'redeem'
        deploy  = 'deploy'
        attack  = 'attack'
        move    = 'move'
        card    = 'card'
        finish  = 'finish'

        states = [initial, redeem, deploy, attack, move, card, finish]

        trans = [  # [name, from|[froms], to]
            {
                'trigger': 'redeem_cards',
                'source': initial,
                'dest': redeem,
                'conditions': '_check_redeem',
                'after': '_do_redeem',
            }, {
                'trigger': 'deploy_troops',
                'source': [initial, redeem, deploy],
                'dest': deploy,
                'conditions': '_check_deploy',
                'after': '_do_deploy',
            }, {
                'trigger': 'attack_country',
                'source': [deploy, attack],
                'dest': attack,
                'conditions': '_check_attack',
                'after': '_do_attack',
            }, {
                'trigger': 'move_troops',
                'source': [deploy, attack, card],
                'dest': move,
                'conditions': '_check_move',
                'after': '_do_move',
            }, {
                'trigger': 'get_card',
                'source': attack,
                'dest': card,
                'conditions': '_check_get_card',
                'after': '_do_get_card',
            }, {
                'trigger': 'end_turn',
                'source': [deploy, attack, card, move],
                'dest': finish,
                # 'after': 'next_move'
            }
        ]

        self.machine = transitions.Machine(
            self,
            states=states,
            transitions=trans,
            initial=initial,
            auto_transitions=False
        )

    # State Machine:
    # _check_X methods verify if action X is allowed for the current player.
    # _do_X methods actually apply action X.
    # Both _check_X and _do_X are called with the same parameters in the
    # following order:
    # 1. _check_X is called to check if a transition in the state machine
    #    is possible with the given parameters. (Return True/ False)
    # 2. If so, _do_X is called with the same parameters to execute the action.
    # Note: If not, neither _do_X and nor any other method is called at all.

    def _check_redeem(self, redeem):
        player_cards = self.current_player.cards.copy()
        redeem_cards, _ = redeem.value

        # check if player has every card needed to redeem what he claims
        for card in redeem_cards:
            try:
                player_cards.remove(card)
            except ValueError:
                # player wants to redeem card but does not have it
                return False

        # player has all cards
        return True

    def _do_redeem(self, redeem):
        player = self.current_player
        player_cards = player.cards

        redeem_cards, value = redeem.value
        player.available_troops += value

        for card in redeem_cards:
            player_cards.remove(card)

        player.notify(Redeemed(redeem))



    def _check_deploy(self, country, troops):
        return (self._current_player_is_owner(country)
                and self.current_player.available_troops >= troops)

    def _do_deploy(self, country, troops):
        country.troops += troops
        self.current_player.available_troops -= troops

        player.notify(Deployed(country, troops))


    def _check_attack(self, origin, destination, attack_troops):
        return (self._current_player_is_owner(origin)
                and not self._current_player_is_owner(destination)
                and origin.troops > attack_troops  # one troop must remain
                and self._between(attack_troops, 1, 3))

    def _do_attack(self, origin, destination, attack_troops):
        attacker = self.current_player
        defender = destination.owner

        defend_troops = min(attack_troops, destination.troops, 2)

        attack_dice = self._roll_dice(attack_troops)
        defend_dice = self._roll_dice(defend_troops)

        attack_losses = 0
        defend_losses = 0
        for (a, d) in zip(attack_dice, defend_dice):
            if a > d:  # attacker won
                defend_losses += 1
            else:  # defender won
                attack_losses += 1

        origin.troops -= attack_losses
        destination.troops -= defend_losses

        if destination.troops == 0:
            # defending country is conquered
            defender.owned_countries -= 1
            attacker.owned_countries += 1

            destination.troops = attack_troops
            destination.owner = attacker

            attacker.conquered_country_in_turn = True

            attacker.notify(Conquered(destination))
            defender.notify(Defeated(destination))
        else:
            attacker.notify(Attacked(destination, attack_losses))
            defender.notify(Defended(destination, defend_losses))

    @staticmethod
    def _roll_dice(n):
        return [random.randint(1, 6) for _ in range(n)].sort(reverse=True)


    def _check_move(self, origin, destination, troops):
        return (self._current_player_is_owner(origin)
                and self._current_player_is_owner(destination)
                and origin.troops > troops)  # at least one troop must remain
                # TODO: do countries have to be neighbours/ connected?

    def _do_move(self, origin, destination, troops):
        origin.troops -= troops
        destination.troops += troops
        self.current_player.notify(Moved(origin, destination, troops))


    def _check_get_card(self):
        return self.current_player.conquered_country_in_turn

    def _do_get_card(self):
        new_card = random.choice(list(Card))
        self.current_player.cards.append(new_card)
        self.current_player.notify(GotCard(new_card))


    def _current_player_is_owner(self, country):
        return country.owner == self.current_player

    @staticmethod
    def _between(value, low, high):
        return low <= value and value <= high

    def next_move(self):
        # TODO: probably more logic to set up the next player's turn
        player = self.players[0]
        self.players.append(self.current_player)
        self.players = self.players[1:]
        self.current_player = player

        player.conquered_country_in_turn = False
        player.available_troops = player.owned_countries // 3

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
