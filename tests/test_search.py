from collections import Counter
import random
import unittest

from morris.board import Board, game_winner, generate_moves, opponent
from morris.evaluation import WIN, improved
from morris.search import fixed_search
from morris.tournament import TournamentSearch, position_key
from tests import reference
from tests.test_rules import make_board


def exhaustive(board, side, placements, depth, counts):
    if placements == 0:
        winner = game_winner(board, side)
        if winner:
            return WIN if winner == side else -WIN
    if counts[position_key(board, side)] >= 3:
        return 0
    if depth == 0:
        return improved(board, placements > 0) * (1 if side == "W" else -1)
    values = []
    for child in generate_moves(board, side, placements > 0):
        key = position_key(child, opponent(side))
        counts[key] += 1
        values.append(-exhaustive(child, opponent(side), max(0, placements - 1), depth - 1, counts))
        counts[key] -= 1
        if not counts[key]:
            del counts[key]
    return max(values, default=-WIN)


class FixedSearchTests(unittest.TestCase):
    def test_minimax_against_string_oracle_and_alpha_beta(self):
        samples = [(Board(0, 0), True, 3),
                   (make_board([0, 3, 7], [2, 5, 9]), True, 3),
                   (Board.parse("xxxxxBxWWWWWBBBBxxxxxxx"), False, 3),
                   (make_board([0, 4, 7], [3, 8, 12, 19]), False, 2)]
        for board, opening, depth in samples:
            expected, move, leaves = reference.minimax(str(board), depth, opening)
            plain = fixed_search(board, depth, opening)
            pruned = fixed_search(board, depth, opening, pruning=True)
            self.assertEqual((plain.score, str(plain.board), plain.evaluations),
                             (expected, move, leaves))
            self.assertEqual((plain.score, plain.board), (pruned.score, pruned.board))
            self.assertLess(pruned.evaluations, plain.evaluations)

    def test_seeded_equivalence_both_colors_and_estimators(self):
        rng = random.Random(31)
        for _ in range(15):
            cells = rng.sample(range(23), 10)
            board = make_board(cells[:5], cells[5:])
            for opening in (True, False):
                for side in ("W", "B"):
                    for enhanced in (False, True):
                        left = fixed_search(board, 2, opening, side=side, enhanced=enhanced)
                        right = fixed_search(board, 2, opening, side=side, enhanced=enhanced, pruning=True)
                        self.assertEqual((left.score, left.board), (right.score, right.board))
                        self.assertLessEqual(right.evaluations, left.evaluations)

    def test_black_color_swap_and_zero_depth(self):
        board = Board.parse("xxxxxBxWWWWWBBBBxxxxxxx")
        for opening in (True, False):
            white = fixed_search(board.swapped(), 2, opening)
            black = fixed_search(board, 2, opening, side="B")
            self.assertEqual((black.board, black.score), (white.board.swapped(), white.score))
        zero = fixed_search(board, 0, True)
        self.assertEqual((zero.board, zero.evaluations), (board, 1))


class TournamentTests(unittest.TestCase):
    def test_scores_against_exhaustive_with_phase_transition_and_history(self):
        samples = [(make_board([0, 4, 7], [2, 9, 12, 18]), "W", 0, 2),
                   (make_board([0, 3, 8, 16], [2, 5, 11, 20]), "B", 1, 3),
                   (make_board([0, 3, 8, 16], [2, 5, 11, 20]), "W", 2, 3),
                   (Board(0, 0), "W", 18, 3)]
        for board, side, placements, depth in samples:
            first = generate_moves(board, side, placements > 0)[0]
            for history in ([], [(first, opponent(side))] * 2):
                counts = Counter(position_key(b, s) for b, s in history)
                counts[position_key(board, side)] += 1
                expected = exhaustive(board, side, placements, depth, counts)
                for use_table in (True, False):
                    result = TournamentSearch(use_table=use_table).choose(
                        board, side, placements, time_limit=30, max_depth=depth, history=history)
                    self.assertEqual(result.score, expected)
                    self.assertIn(result.board, generate_moves(board, side, placements > 0))

    def test_time_limit_retains_last_completed_legal_move(self):
        now = [0.0]

        def clock():
            now[0] += 0.001
            return now[0]

        saved = []
        result = TournamentSearch(clock=clock).choose(
            Board(0, 0), "W", 18, time_limit=0.08, on_complete=lambda r: saved.append(r.board))
        self.assertTrue(result.timed_out)
        self.assertGreaterEqual(result.depth, 1)
        self.assertEqual(saved[-1], result.board)
        self.assertIn(result.board, generate_moves(Board(0, 0), "W", True))
        self.assertLess(result.elapsed, 0.09)

    def test_timeout_before_first_iteration_still_checkpoints(self):
        ticks = iter([0, 1, 2])
        saved = []
        result = TournamentSearch(clock=lambda: next(ticks)).choose(
            Board(0, 0), "W", 18, time_limit=0.001, on_complete=lambda r: saved.append(r.board))
        self.assertEqual(result.depth, 0)
        self.assertEqual(saved, [make_board([0])])

    def test_terminal_and_third_repetition_rejected(self):
        board = make_board([0, 4, 7, 10], [2, 5, 12, 18])
        with self.assertRaisesRegex(ValueError, "draw"):
            TournamentSearch().choose(board, "W", 0, history=[(board, "W")] * 2)
        with self.assertRaisesRegex(ValueError, "ended"):
            TournamentSearch().choose(make_board([0, 1], [2, 3, 5]), "W", 0)

    def test_repetition_value_cache_is_history_sensitive(self):
        board = make_board([0, 4, 7, 10], [2, 5, 12, 18])
        engine = TournamentSearch()
        key = position_key(board, "W")
        engine.counts[key] = 1
        normal, _ = engine._visit(board, "W", 0, 2, -10**12, 10**12)
        for child in generate_moves(board, "W", False):
            engine.counts[position_key(child, "B")] = 2
        drawn, _ = engine._visit(board, "W", 0, 2, -10**12, 10**12)
        self.assertEqual(drawn, 0)
        self.assertNotEqual(normal, drawn)

    def test_shallow_transpositions_actually_reduce_search(self):
        results = []
        for enabled in (False, True):
            engine = TournamentSearch(use_table=enabled)
            result = engine.choose(Board(0, 0), "W", 18, max_depth=4, time_limit=30)
            results.append(result)
            if enabled:
                self.assertGreater(engine.hits, 0)
        self.assertEqual(results[0].score, results[1].score)
        self.assertLess(results[1].nodes, results[0].nodes)

    def test_invalid_time_budgets(self):
        for value in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                TournamentSearch().choose(Board(0, 0), "W", 18, time_limit=value)

    def test_winning_capture_for_both_colors(self):
        board = make_board([0, 1, 7], [3, 5, 8])
        for position, side in ((board, "W"), (board.swapped(), "B")):
            result = TournamentSearch().choose(position, side, 0, time_limit=1, max_depth=2)
            self.assertEqual(result.score, WIN)
            self.assertEqual(result.board.pieces(opponent(side)).bit_count(), 2)

    def test_last_placement_does_not_lose_prematurely(self):
        board = make_board([0, 4, 7], [2, 8])
        result = TournamentSearch().choose(board, "B", 1, time_limit=1, max_depth=1)
        self.assertEqual(result.board.black.bit_count(), 3)
        self.assertLess(abs(result.score), WIN)

    def test_repetition_requires_same_side_to_move(self):
        board = make_board([0, 4, 7, 10], [2, 5, 12, 18])
        result = TournamentSearch().choose(board, "W", 0, max_depth=1,
                                           time_limit=1, history=[(board, "B")] * 2)
        self.assertEqual(result.depth, 1)
