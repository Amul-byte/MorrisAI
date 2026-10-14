import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from morris.board import Board, generate_moves
from TournamentAgent import load_history, validate_position, validate_transition
from tests.test_rules import make_board

ROOT = Path(__file__).resolve().parents[1]


class CommandLineTests(unittest.TestCase):
    def test_all_eight_entry_points(self):
        scripts = {
            "MiniMaxOpening": (True, "W"), "ABOpening": (True, "W"),
            "MiniMaxGame": (False, "W"), "ABGame": (False, "W"),
            "MiniMaxOpeningBlack": (True, "B"), "MiniMaxGameBlack": (False, "B"),
            "MiniMaxOpeningImproved": (True, "W"), "MiniMaxGameImproved": (False, "W"),
        }
        with tempfile.TemporaryDirectory() as temp:
            source, target = Path(temp) / "in.txt", Path(temp) / "out.txt"
            board = Board.parse("xxxxxBxWWWWWBBBBxxxxxxx")
            source.write_text(str(board) + "\n")
            for script, (opening, side) in scripts.items():
                run = subprocess.run([sys.executable, str(ROOT / (script + ".py")),
                                      str(source), str(target), "2"],
                                     capture_output=True, text=True, timeout=30)
                self.assertEqual(run.returncode, 0, run.stderr)
                chosen = Board.parse(target.read_text())
                self.assertIn(chosen, generate_moves(board, side, opening))
                lines = run.stdout.splitlines()
                self.assertEqual(lines[0], f"Board Position: {chosen}")
                self.assertTrue(lines[1].startswith("Positions evaluated by static estimation: "))
                self.assertTrue(lines[2].startswith("MINIMAX estimate: "))

    def test_invalid_input_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as temp:
            source, target = Path(temp) / "in.txt", Path(temp) / "out.txt"
            source.write_text("bad board")
            target.write_text("do not overwrite")
            run = subprocess.run([sys.executable, str(ROOT / "ABOpening.py"),
                                  str(source), str(target), "2"], capture_output=True, text=True)
            self.assertNotEqual(run.returncode, 0)
            self.assertEqual(target.read_text(), "do not overwrite")

    def test_tournament_history_and_opponent_reply(self):
        with tempfile.TemporaryDirectory() as temp:
            source, target, log = [Path(temp) / name for name in ("in.txt", "out.txt", "game.json")]
            source.write_text("x" * 23)
            for number, side in ((1, "W"), (2, "B"), (3, "W")):
                run = subprocess.run([sys.executable, str(ROOT / "TournamentAgent.py"),
                                      str(source), str(target), "--side", side,
                                      "--move-number", str(number), "--time-limit", "0.08",
                                      "--history", str(log)], capture_output=True, text=True, timeout=5)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertIn(f"Move {number} - ", run.stdout)
                source.write_text(target.read_text())
            entries = json.loads(log.read_text())
            self.assertEqual([e["move"] for e in entries], [1, 2, 3, 4])
            bad = Board.parse("xxxxxxxxxxxxxxxxxxxxxxB")
            with self.assertRaises(ValueError):
                load_history(log, bad, "B", 4)

    def test_move_number_validation(self):
        with self.assertRaises(ValueError):
            validate_position(Board(0, 0), "B", 1)
        with self.assertRaises(ValueError):
            validate_position(Board(3, 0), "W", 1)

    def test_history_cannot_continue_after_terminal(self):
        before = make_board([0, 1], [3, 5, 8])
        after = generate_moves(before, "W", False)[0]
        with self.assertRaisesRegex(ValueError, "ended"):
            validate_transition({"move": 19, "turn": "W", "board": str(before)},
                                {"move": 20, "turn": "B", "board": str(after)})

    def test_malformed_history_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            log = Path(temp) / "bad.json"
            log.write_text('[{"board": 23, "move": 1, "turn": "W"}]')
            with self.assertRaises(ValueError):
                load_history(log, Board(0, 0), "W", 1)


if __name__ == "__main__":
    unittest.main()
