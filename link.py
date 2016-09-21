from enum import Enum
import json


class Message(object):
  """Message/ Event. Subclasses need to implement method json_data()."""
  class Type(Enum):
    """Message Type"""
    Echo = 1
    Move = 2

  def __init__(self, msg_type):
    self.type = msg_type

  def json_data(self):
    return str(self)

  def json(self):
    data = self.json_data()
    return {
        'type': self.type,
        'data': data
    }

class MessageParser(object):
  """Parser for Messages"""
  def parse(self, payload):
    try:
      message = json.loads(payload)
      return (Message.Type(message['type']), message['data'])
    except Exception:
      raise ParseError()

class ParseError(Exception):
  """Thrown when parsing fails."""
  pass
