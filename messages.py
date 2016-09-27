from enum import Enum, unique


class Message(object):
    """Message/ Event. Subclasses should implement _json_data or json."""
    # https://docs.python.org/3/library/asyncio-sync.html#event
    @unique
    class Type(Enum):
        """Message type. Can be used as a decorator(see __call__)."""
        # Messages from players
        Echo = 1
        Deploy = 2
        Attack = 3
        Move = 4
        Finished = 5
        Board = 6
        Players = 7
        Card = 8
        Redeem = 9
        GameEnd = 10
        Kick = 11
        Quit = 12

        # Answers to players
        Redeemed = 13
        Deployed = 14
        Conquered = 15
        Defeated = 16
        Attacked = 17
        Defended = 18
        Moved = 19
        GotCard = 20

        def __call__(self, cls):
            cls.type = self
            return cls

    def __init__(self, data, id = None):
        for attr in self.fields:
            try:
                setattr(self, attr, data[attr])
            except KeyError:
                raise ValueError('Missing field %s' % attr)

        self.id = id

    def _json_data(self):
        data = {}
        for attr in self.fields:
            data[attr] = getattr(self, attr)

        return data

    def json(self):
        json = {
            'type': self.type.value,
            'data': self._json_data()
        }
        if self.id is not None:
            json['id'] = self.id

        return json

@Message.Type.Deployed
class Deployed(Message):
    fields = ['country', 'troops']


@Message.Type.Redeemed
class Redeemed(Message):
    def __init__(self, redeem):
        self.redeem = redeem

    def _json_data(self):
        return {
            'value': redeem.value[1]
        }


@Message.Type.Deployed
class Deployed(Message):
    def __init__(self, country, troops):
        self.country = country
        self.troops = troops

    def _json_data(self):
        return {
            'country': self.country.name,
            'troops': self.troops
        }


@Message.Type.Conquered
class Conquered(Message):
    def __init__(self, country):
        self.country = country

    def _json_data(self):
        return {
            'country': self.country.name
        }


@Message.Type.Defeated
class Defeated(Message):
    def __init__(self, country):
        self.country = country

    def _json_data(self):
        return {
            'country': self.country.name
        }


@Message.Type.Attacked
class Attacked(Message):
    def __init__(self, country, losses):
        self.country = country
        self.losses = losses

    def _json_data(self):
        return {
            'country': self.country.name,
            'losses': self.losses
        }


@Message.Type.Defended
class Defended(Message):
    def __init__(self, country, losses):
        self.country = country
        self.losses = losses

    def _json_data(self):
        return {
            'country': self.country.name,
            'losses': self.losses
        }


@Message.Type.Moved
class Moved(Message):
    def __init__(self, origin, destination, troops):
        self.origin = origin
        self.destination = destination
        self.troops = troops

    def _json_data(self):
        return {
            'origin': self.origin.name,
            'destination': self.destination.name,
            'troops': self.troops
        }


@Message.Type.GotCard
class GotCard(Message):
    def __init__(self, card):
        self.card = card

    def _json_data(self):
        return {
            'card': self.card.value
        }
