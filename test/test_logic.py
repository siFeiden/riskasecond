from unittest import TestCase

import risk.logic
import risk.board


class TestLogic(TestCase):
    """Test the Logic module."""

    def setUp(self):
        self.p1 = 'Player 1'
        self.p2 = 'Player 2'
        self.p3 = 'Player 3'
        self.board = risk.board.Board()
        self.logic = risk.logic.Logic(self.board, [self.p1, self.p2])

    def test_is_ingame(self):
        self.assertTrue(self.logic.is_ingame(self.p1))
        self.assertTrue(self.logic.is_ingame(self.p2))
        self.assertFalse(self.logic.is_ingame(self.p3))

    def test_kick(self):
        self.assertTrue(self.logic.is_ingame(self.p1))
        self.assertTrue(self.logic.is_ingame(self.p2))

        self.logic.kick(self.p1)

        self.assertFalse(self.logic.is_ingame(self.p2))

        for country in self.board.countries_list():
            with self.subTest(country=country):
                self.assertNotEqual(country.owner, self.p1)
