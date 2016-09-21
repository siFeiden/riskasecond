from collections import defaultdict
import random

class Board(object):
  """A Board of the Risk game. Manages ownership of countries etc."""
  def __init__(self):
    # TODO: builder or parser for Maps

    # small static Map
    """
      ger -- usa
       |  \   |
      tha    aus
    """

    ger = Country('Germany')
    usa = Country('USA')
    tha = Country('Thailand')
    aus = Country('Australia')

    self.countryNames = {
      'Germany': ger,
      'USA': usa,
      'Thailand': tha,
      'Australia': aus
    }
    self.countries = [ger, usa, tha, aus]
    self.edges = defaultdict(list, {
      ger: [usa, aus, tha],
      usa: [ger, aus],
      tha: [ger],
      aus: [ger, usa]
    })

  def countries(arg, country):
    return list(self.countries)

  def move_troops(self, origin, destination, troops):
    # TODO: range checks
    # TODO: check movement logic
    origin = self.countryNames[origin]
    destination = self.countryNames[destination]

    if destination.troops == 0:
      destination.owner = origin.owner

    origin.troops -= troops
    destination.troops += troops

  def attack_country(self, origin, destination, attack_troops, defend_troops):
    # TODO: range checks
    # TODO: correct attacking logic
    origin = self.countryNames[origin]
    destination = self.countryNames[destination]

    # some arbitrary logic as prototype
    if r.randint(0, 1): # attacker wins
      origin.troops -= attack_troops - 1
      destination.troops = attack_troops - a
    else: # defender wins
      origin.troops -= attack_troops

class Country(object):
  """A Country in a Risk Map"""
  def __init__(self, name, owner = None, troops = 0):
    self.name = name
    self.owner = owner
    self.troops = troops

  def __eq__(self, other):
    return self.name == other.name

  def __hash__(self):
    return hash(self.name)
