from enum import Enum, unique
import random

from statemachine import Machine

from . import messages as m


@unique
class Card(Enum):
    """Bonus Card."""
    INFANTRY = 1
    CAVALRY = 2
    ARTILLERY = 3


class Bonus(Enum):
    """Trade in three cards for bonus troops."""
    INFANTRY = ([Card.INFANTRY]  * 3, 4)
    CAVALRY = ([Card.CAVALRY]   * 3, 6)
    ARTILLERY = ([Card.ARTILLERY] * 3, 8)
    MIXED = ([Card.INFANTRY, Card.CAVALRY, Card.ARTILLERY], 10)


class Player(object):
    """
    Wrap a player identifier with additional information used during a game.
    """

    def __init__(self, ident):
        """The player identifier."""
        self.ident = ident
        """Number of countries this player owns."""
        self.owned_countries = 0
        """Flag to check if the player may draw a card."""
        self.conquered_country_in_turn = False
        """Troops the player may deploy in this turn."""
        self.available_troops = 0
        """The player's bonus cards."""
        self.cards = []

    def __eq__(self, other):
        return self.ident == other.ident

    def __ne__(self, other):
        return self.ident != other.ident

    def __hash__(self):
        return hash(self.ident)


class Action(object):
    """
    Base class for actions that can be performed during a game.

    This class models actions for a game and is supposed to be extended.
    Each action must fulfill certain preconditions before being executed.
    Use is_permitted() to check the preconditions for the action and
    execute() to apply the action to the current game state.
    An action instance is used during the whole game for every turn.
    At the start of every turn, next_turn() is called is called with the
    new current player. Before checks and execution, prepare() is called.
    To simplify communicating the result or effects of an action,
    answer() can be used to send messages to the players that are affected.

    Attributes:
    board, current_player, current_message, success

    Methods:
    prepare, is_permitted, execute, next_turn, answer
    """

    def __init__(self, board):
        self.board = board
        self.current_player = None
        self.current_message = None

    def prepare(self, message):
        """Extend this method to store properties of the message."""
        self.current_message = message

    def is_permitted(self, _):
        """Extend this method to check if the action is allowed."""
        # TODO: check if executing player is current player
        return True

    def execute(self, _):
        """Override this method to execute the action."""
        pass

    def next_turn(self, player):
        """Extend/ Override this method to prepare for the next turn."""
        self.current_player = player

    def answer(self, message, player=None):
        """
        Store an answer to be sent to the given player.
        If player is None, the current player is used as recipient.
        """
        if player is None:
            player = self.current_player

        self.current_message.add_answer(player.ident, message)

    @property
    def success(self):
        return self.current_message.success

    @success.setter
    def success(self, success):
        self.current_message.success = success


class BonusAction(Action):
    def prepare(self, message):
        super().prepare(message)
        self.bonus = None  # TODO

    def is_permitted(self, _):
        player_cards = self.current_player.cards.copy()
        bonus_cards, _ = self.bonus.value

        # check if player has every card needed to redeem what he claims
        for card in bonus_cards:
            try:
                player_cards.remove(card)
            except ValueError:
                # player wants to trade in card but does not have it
                return False

        # player has all cards
        return True

    def execute(self, _):
        player = self.current_player
        player_cards = player.cards

        bonus_cards, value = self.bonus.value
        player.available_troops += value

        for card in bonus_cards:
            player_cards.remove(card)

        self.success = True


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

        self.success = True


class AttackAction(Action):
    def prepare(self, message):
        super().prepare(message)
        self.origin = self.board.country_for_name(message.origin)
        self.destination = self.board.country_for_name(message.destination)
        self.attack_troops = message.attack_troops


    def is_permitted(self, _):
        return (self._current_player_is_owner(self.origin)
                and not self._current_player_is_owner(self.destination)
                # use > since one troop must remain on attacking country
                and self.origin.troops > self.attack_troops
                and self.attack_troops >= 1
                and self.attack_troops <= 3)

    def _current_player_is_owner(self, country):
        return self.current_player == country.owner

    def execute(self, _):
        attacker = self.current_player
        defender = self.destination.owner

        attack_troops = self.attack_troops
        defend_troops = min(self.attack_troops, self.destination.troops, 2)

        attack_losses, defend_losses = self._fight_for_country(
            attack_troops, defend_troops
        )

        self.origin.troops -= attack_losses
        self.destination.troops -= defend_losses

        if self.destination.troops == 0:
            # defending country is conquered
            attacker.owned_countries += 1
            defender.owned_countries -= 1

            self.destination.troops = attack_troops
            self.destination.owner = attacker

            attacker.conquered_country_in_turn = True

            self.answer(m.Conquered(self.destination), attacker)
            self.answer(m.Defeated(self.destination), defender)
        else:
            self.success = True
            self.answer(m.Defended(self.destination, defend_losses), defender)

    def _fight_for_country(self, attack_troops, defend_troops):
        attack_dice = self._roll_dice(attack_troops)
        defend_dice = self._roll_dice(defend_troops)

        attack_losses = 0
        defend_losses = 0
        for (attack_score, defend_score) in zip(attack_dice, defend_dice):
            if attack_score > defend_score:  # attacker won
                defend_losses += 1
            else:  # defender won
                attack_losses += 1

        return attack_losses, defend_losses

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
                # use > since at least one troop must remain in origin country
                and self.origin.troops > self.troops)
                # TODO: do countries have to be neighbours/ connected?

    def _current_player_is_owner(self, country):
        return self.current_player == country.owner

    def execute(self, _):
        self.origin.troops -= self.troops
        self.destination.troops += self.troops
        self.success = True


class GetCardAction(Action):
    def is_permitted(self, _):
        return self.current_player.conquered_country_in_turn

    def execute(self, _):
        new_card = random.choice(list(Card))
        self.current_player.cards.append(new_card)
        self.success = True


class NextTurnAction(Action):
    def __init__(self, board, players, actions):
        super().__init__(board)
        # contains all players except the current one
        self.players = players[1:]
        # player whose turn it is now
        self.current_player = players[0]
        self.actions = actions

    def next_turn(self, player):
        pass

    def execute(self, _):
        # rotate list with current player
        self.players.append(self.current_player)
        self.current_player = self.players[0]
        self.players = self.players[1:]

        # TODO: probably more logic to set up the next player's turn
        player = self.current_player
        player.conquered_country_in_turn = False
        player.available_troops = player.available_troops // 3

        for action in self.actions:
            action.next_turn(player)


class Logic(object):
    """
    Contains the Logic for a game of Risk.

    Each turn in a game is a sequence of actions by the current
    player. Each action is modelled by the Action class and used
    here in a state machine that allows all possible actions only
    if they are allowed according to the game's rules.

    Attributes:
    board, players, machine

    Public Methods:
    distribute_countries, is_ingame, kick
    """

    def __init__(self, board, players):
        """ Create a new Logic for the given board and players."""

        """Store the board of the game."""
        self.board = board

        """Store all participating players"""
        self.players = []
        for ident in players:
            self.players.append(Player(ident))

        self.distribute_countries()

        # State machine that checks if an action is
        # allowed for the current player right now
        # and if so performs the action.

        # states
        before_start = 'before_start'  # before the first move
        start_of_turn = 'start_of_turn'  # at the start of a player's turn
        got_bonus = 'got_bonus'  # player traded cards for a bonus
        deploying = 'deploying'  # player is deploying troops
        attacking = 'attacking'  # player is attacking others
        drew_card = 'drew_card'  # player drew a card after attacking
        moved = 'moved'  # player moved troops

        # actions
        bonus = BonusAction(board)
        deploy = DeployAction(board)
        attack = AttackAction(board)
        get_card = GetCardAction(board)
        move = MoveAction(board)

        actions = [bonus, deploy, attack, get_card, move]
        next_turn = NextTurnAction(board, players, actions)


        states = [before_start, start_of_turn, got_bonus,
                  deploying, attacking, moved, drew_card]

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
            make_transition('bonus', start_of_turn, got_bonus, bonus),
            make_transition('deploy', [start_of_turn, got_bonus, deploying],
                            deploying, deploy),
            make_transition('attack', [deploying, attacking],
                            attacking, attack),
            make_transition('draw_card', attacking, drew_card, get_card),
            make_transition('move', [deploying, attacking, drew_card],
                            moved, move),
            make_transition('next_turn', [before_start, deploying, attacking,
                            drew_card, moved], start_of_turn, next_turn)
        ]

        self.machine = Machine(
            self,
            states=states,
            transitions=trans,
            initial=before_start,
            auto_transitions=False
        )

    def distribute_countries(self):
        """
        Distribute the board's countries to the participating players.
        Changes the owner attribute of the countries stored in the board.
        """
        # TODO: is this a fair distribution?
        num_players = len(self.players)
        countries = self.board.countries_list()
        random.shuffle(countries)

        for i, country in enumerate(countries):
            player = self.players[i % num_players]
            country.owner = player
            player.owned_countries += 1

    def is_ingame(self, player):
        """Check if a player participates in the game."""
        participants = self.players

        if not isinstance(player, Player):
            participants = map(lambda p: p.ident, participants)

        return player in participants

    def kick(self, player):
        """Kick a player from the game."""
        # TODO: remove player from game, board, etc.
        # TODO: unskip test
        print('kick idiot', self.players, player)
