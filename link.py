from enum import Enum
import json


class Message(object):
    """Message/ Event. Subclasses should implement method _json_data or json."""
    class Type(Enum):
        """Message Type"""
        Echo = 1

    def __init__(self, msg_type):
        self.type = msg_type

    def _json_data(self):
        return str(self)

    def json(self):
        data = self._json_data()
        return {
            'type': self.type.value,
            'data': data
        }

class EchoMessage(Message):
    """docstring for EchoMessage."""
    def __init__(self, data):
        super(EchoMessage, self).__init__(Message.Type.Echo)
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

            return message_class(message_data)
        except (json.JSONDecodeError, ValueError, KeyError):
            raise ParseError


class ParseError(Exception):
    """Thrown when parsing fails."""
    pass
