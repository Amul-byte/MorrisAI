import random
import unittest

from morris.board import (Board, FULL, MILLS, NEIGHBORS, closes_mill,
                          game_winner, generate_moves)
from morris.evaluation import baseline, features, improved
from tests import reference


def make_board(white=(), black=()):
    return Board(sum(1 << i for i in white), sum(1 << i for i in black))


class BoardTests(unittest.TestCase):
    def test_validation_and_roundtrip(self):
        example = "xxxxxBxWWWWWBBBBxxxxxxx"
        self.assertEqual(str(Board.parse(example + "\n")), example)
        for invalid in ("x" * 22, "x" * 24, "w" + "x" * 22, "x" * 11 + " " + "x" * 11):
            with self.assertRaises(ValueError):
                Board.parse(invalid)
        for masks in ((1, 1), (-1, 0), (FULL + 1, 0)):
            with self.assertRaises(ValueError):
                Board(*masks)

    def test_topology_against_independent_diagram(self):
        self.assertEqual(set(map(frozenset, MILLS)), set(map(frozenset, reference.TRIPLES)))
        self.assertEqual(len(MILLS), 18)
        for i, neighbors in enumerate(NEIGHBORS):
            self.assertEqual(set(neighbors), reference.ADJACENT[i])
            for j in neighbors:
                self.assertIn(i, NEIGHBORS[j])
        # The absent d2 means c2/e2 is an edge, never a three-point mill.
        self.assertIn(7, NEIGHBORS[6])
        self.assertFalse(closes_mill((1 << 6) | (1 << 7), 6))

    def test_all_mills_and_broken_mills(self):
        for triple in reference.TRIPLES:
            pieces = sum(1 << i for i in triple)
            for i in triple:
                self.assertTrue(closes_mill(pieces, i))
                self.assertFalse(closes_mill(pieces ^ (1 << i), i))

    def test_empty_opening(self):
        moves = generate_moves(Board(0, 0), "W", True)
        self.assertEqual(len(moves), 23)
        self.assertEqual(moves[0], make_board([0]))

    def test_capture_isolated_only_and_all_protected_fallback(self):
        board = make_board([3, 4], [8, 9, 10, 22])
        closing = [m for m in generate_moves(board, "W", True) if m.white & (1 << 5)]
        self.assertEqual(closing, [make_board([3, 4, 5], [8, 9, 10])])
        protected = make_board([3, 4], [8, 9, 10])
        closing = [m for m in generate_moves(protected, "W", True) if m.white & (1 << 5)]
        self.assertEqual(closing, [make_board([3, 4, 5], [8, 9, 10])])

    def test_double_mill_captures_only_one(self):
        board = make_board([1, 2, 3, 6], [11, 14, 21])
        closing = [m for m in generate_moves(board, "W", True) if m.white & 1]
        self.assertEqual(len(closing), 3)
        self.assertTrue(all(m.black.bit_count() == 2 for m in closing))

    def test_hopping_only_at_three(self):
        three = make_board([0, 4, 7], [8, 12, 18, 21])
        hopped = make_board([4, 7, 22], [8, 12, 18, 21])
        self.assertIn(hopped, generate_moves(three, "W", False))
        four = make_board([0, 4, 7, 10], [8, 12, 18, 21])
        self.assertNotIn(make_board([4, 7, 10, 22], [8, 12, 18, 21]),
                         generate_moves(four, "W", False))

    def test_blocked_and_material_terminals(self):
        blocked = make_board([0, 1, 2, 4], [3, 5, 8, 13])
        self.assertEqual(game_winner(blocked, "W"), "B")
        self.assertEqual(game_winner(make_board([0, 1], [3, 5, 8]), "W"), "B")

    def test_opening_three_pieces_do_not_receive_hopping_mobility(self):
        board = make_board([0, 4, 7], [8, 12, 18, 21])
        opening = features(board.white, board.black, True)
        game = features(board.white, board.black, False)
        self.assertLess(opening[4], 12)
        self.assertEqual(game[4], 3 * 16)

    def test_slide_does_not_count_its_vacated_support_as_a_threat(self):
        # 0,1 -> 2 is not a genuine threat: moving 1 empties the same mill.
        board = make_board([0, 1, 9, 18], [3, 11, 20, 22])
        self.assertEqual(features(board.white, board.black, False)[2], 0)

    def test_random_differential_moves_evaluations_and_color_symmetry(self):
        rng = random.Random(4346)
        for _ in range(300):
            cells = rng.sample(range(23), 18)
            w, b = rng.randrange(10), rng.randrange(10)
            board = make_board(cells[:w], cells[9:9 + b])
            original = str(board)
            for opening in (True, False):
                self.assertEqual(baseline(board, opening), reference.baseline(original, opening))
                # Avoid impossible both-sides-terminal boards for antisymmetry.
                if opening or min(w, b) >= 3:
                    self.assertEqual(improved(board, opening), -improved(board.swapped(), opening))
                for side in ("W", "B"):
                    actual = generate_moves(board, side, opening)
                    self.assertEqual(list(map(str, actual)), reference.moves(original, side, opening))
                    swapped = generate_moves(board.swapped(), "B" if side == "W" else "W", opening)
                    self.assertEqual(actual, [child.swapped() for child in swapped])
                    self.assertEqual(len(actual), len(set(actual)))
            self.assertEqual(str(board), original)

    def test_reachable_games_against_oracle(self):
        rng = random.Random(42)
        positions = 0
        for _ in range(12):
            board = Board(0, 0)
            for ply in range(90):
                side = "W" if ply % 2 == 0 else "B"
                if ply >= 18 and game_winner(board, side):
                    break
                moves = generate_moves(board, side, ply < 18)
                self.assertEqual(list(map(str, moves)), reference.moves(str(board), side, ply < 18))
                positions += 1
                board = rng.choice(moves)
        self.assertGreater(positions, 300)
