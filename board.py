from collections import defaultdict
import random


class Country(object):
    """A Country in a Risk Map"""
    def __init__(self, name, owner=None, troops=0):
        self.name = name
        self.owner = owner
        self.troops = troops

    def __eq__(self, other):
        return self.name == other.name

    def __ne__(self, other):
        return self.name != other.name

    def __hash__(self):
        return hash(self.name)


class Board(object):
    """A Board of the Risk game. Manages ownership of countries etc."""
    def __init__(self):
        # TODO: builder or parser for Maps

        # small static Map
        r"""
        ger -- usa
         |  \   |
        tha    aus
        """

        ger = Country('Germany')
        usa = Country('USA')
        tha = Country('Thailand')
        aus = Country('Australia')

        self.country_names = {
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

    def countries_list(self):
        return list(self.countries)
