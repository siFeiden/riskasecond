from enum import Enum, unique
import json


class Message(object):
    """Message/ Event. Subclasses should implement method _json_data or json."""
    @unique
    class Type(Enum):
        """Message type. Can be used as a decorator."""
        Echo = 1
        Deploy = 2
        Attack = 3
        Move = 4
        Finished = 5
        Board = 6
        Players = 7
        Card = 8
        BonusTroops = 9
        GameEnd = 10
        Kick = 11
        Quit = 12

        def __call__(self, cls):
            cls.type = self
            return cls

    def _json_data(self):
        raise NotImplementedError

    def json(self):
        return {
            'type': self.type.value,
            'data': self._json_data()
        }


@Message.Type.Echo
class EchoMessage(Message):
    """Replies with the content."""
    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data


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


"""
class Message(object):
    def __init__(self, fields, data):
        for attr in fields:
            try:
                setattr(self, attr, data[attr])
            except KeyError:
                raise ParseError("Missing field %s" % attr)

    def _json_data(self):
        raise NotImplementedError

    def json(self):
        data = self._json_data()
        return {
            'type': self.type.value,
            'data': data
        }


def messageClassFactory(name, fields, base_class=Message):
    def __init__(self, data):
        base_class.__init__(self, fields, data)

    def _json_data(self):
        json_data = {}
        for attr in fields:
            json_data[attr] = getattr(self, attr)
        return json_data

    new_class = type(name, (base_class,), {
        '__init__', __init__,
        '_json_data', _json_data,
    })

    return new_class
"""
