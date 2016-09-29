from enum import Enum, unique
import json


class Message(object):
    """
    Message/ Event. Subclasses must define a type field with a value
    from Message.Type.
    """
    @unique
    class Type(Enum):
        """Message type. Can be used as a class decorator(see __call__)."""
        Echo = 1
        Deploy = 2

        Attack = 3
        Conquered = 4
        Defeated = 5
        Defended = 6

        Move = 7
        Card = 8
        Bonus = 9

        # not yet implemented
        GameEnd = 10
        Kick = 11
        Quit = 12
        Finished = 13

        def __call__(self, cls):
            cls.type = self
            return cls


    fields = []

    def __init__(self, data, ident=None):
        for attr in self.fields:
            try:
                setattr(self, attr, data[attr])
            except KeyError:
                raise ValueError('Missing field %s' % attr)

        self.ident = ident
        self.success = None
        self.answers = []

    def _json_data(self):
        data = {}
        for attr in self.fields:
            data[attr] = getattr(self, attr)

        return data

    def json(self):
        message_json = {
            'type': self.type.value,
            'data': self._json_data()
        }
        if self.ident is not None:
            message_json['id'] = self.ident
        if self.success is not None:
            message_json['success'] = self.success

        return message_json

    def answer(self, message):
        self.answers.append(message)


@Message.Type.Echo
class EchoMessage(Message):
    def __init__(self, data, ident=None):
        super().__init__(data, ident)
        self.data = data

    def _json_data(self):
        return self.data


@Message.Type.Deploy
class Deploy(Message):
    fields = ['country', 'troops']


@Message.Type.Attack
class Attack(Message):
    fields = ['origin', 'destination', 'attack_troops']


@Message.Type.Conquered
class Conquered(Message):
    fields = ['country']


@Message.Type.Defeated
class Defeated(Message):
    fields = ['country']


@Message.Type.Defended
class Defended(Message):
    fields = ['country', 'losses']


@Message.Type.Move
class Move(Message):
    fields = ['origin', 'destination', 'troops']


@Message.Type.Card
class Card(Message):
    fields = ['card']


@Message.Type.Bonus
class Bonus(Message):
    # TODO: see logic.py:84
    fields = ['bonus']


class MessageParser(object):
    """Parser for Messages"""
    def __init__(self):
        self.type_to_class = {
            Message.Type.Echo: EchoMessage
        }

    def parse(self, payload):
        try:
            payload_json = json.loads(payload)
            message_type = Message.Type(payload_json['type'])
            message_class = self.type_to_class[message_type]
            message_data = payload_json['data']
            message_id = payload_json.get('id', None)

            return message_class(message_data, message_id)
        except (json.JSONDecodeError, ValueError, KeyError):
            raise ParseError


class ParseError(Exception):
    """Thrown when parsing fails."""
    pass
