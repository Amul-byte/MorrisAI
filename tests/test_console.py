import json
from pathlib import Path
import tempfile
import unittest

from morris.board import Board, generate_moves
import TournamentAgent as agent


def scripted(lines):
    """A read() that returns the given lines, then behaves like Ctrl-D."""
    pending = iter(lines)

    def read(prompt):
        try:
            return next(pending)
        except StopIteration:
            raise EOFError from None
    return read


class ConsoleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp.name)
        self.output = []

    def tearDown(self):
        self.temp.cleanup()

    def run_console(self, lines):
        code = agent.run_console(scripted(lines), self.output.append, self.dir)
        return code, "\n".join(self.output)

    def session(self):
        [path] = self.dir.glob("*.json")
        return path, json.loads(path.read_text())

    def test_white_game_rejects_bad_input_and_accepts_two_line_teams_paste(self):
        start = Board.parse("x" * 23)
        lines = ["", "white", "0.05", "2"]
        code, _ = self.run_console(lines + ["quit"])
        self.assertEqual(code, 0)
        path, saved = self.session()
        ours = Board.parse(saved["history"][-1]["board"])
        self.assertIn(ours, generate_moves(start, "W", True))
        reply = generate_moves(ours, "B", True)[0]
        self.output.clear()
        code, text = self.run_console([
            "resume", str(path),
            "not a board", str(ours), f"Move 3 - Black {reply}", "time abc", "depth 0",
            "time 0.05", "show", "Move 2 - Black", str(reply), "quit"])
        self.assertEqual(code, 0)
        self.assertIn("do not post it twice", text)
        self.assertIn("A board must contain exactly 23 characters", text)
        self.assertIn("That is the current board", text)
        self.assertIn("Expected Move 2 - Black", text)
        self.assertEqual(text.count("Settings unchanged"), 2)
        self.assertIn("Next searches: up to 0.05s", text)
        self.assertIn("COPY THESE TWO LINES INTO TEAMS:\nMove 3 - White", text)
        history = self.session()[1]["history"]
        self.assertEqual([e["move"] for e in history], [1, 2, 3, 4])
        self.assertEqual(history[2]["board"], str(reply))
        self.assertIn(Board.parse(history[3]["board"]), generate_moves(reply, "W", True))
        self.assertEqual(self.session()[1]["seconds"], 0.05)

    def test_black_waits_for_white_and_rejects_illegal_reply(self):
        white = "W" + "x" * 22
        code, text = self.run_console(["new", "b", "0.05", "2", "WWxxxxxxxxxxxxxxxxxxxxx",
                                       white.lower(), "quit"])
        self.assertEqual(code, 0)
        self.assertIn("Opponent move is valid", text)
        self.assertIn("not a legal reply", text)
        self.assertIn("Move 2 - Black", text)
        history = self.session()[1]["history"]
        self.assertEqual(history[1]["board"], white)
        self.assertIn(Board.parse(history[2]["board"]), generate_moves(Board.parse(white), "B", True))

    def test_ctrl_d_saves_and_bad_session_file_fails_cleanly(self):
        code, text = self.run_console(["", "w", "0.05", "2"])
        self.assertEqual(code, 0)
        self.assertIn("Stopped. Accepted moves are already saved.", text)
        bad = self.dir / "bad.json"
        bad.write_text('{"version": 1, "side": "W", "seconds": 999, "depth": 2, "history": []}')
        self.output.clear()
        code, _ = self.run_console(["resume", str(bad)])
        self.assertEqual(code, 2)

    def test_game_over_detection(self):
        lost = {"move": 25, "turn": "W", "board": "WWxxxxxBBBxxxxxxxxxxxxx"}
        self.assertEqual(agent.game_over([lost]), "B")
        repeated = {"move": 30, "turn": "B", "board": "WWWxxxxBBBxxxxxxxxxxxxx"}
        self.assertEqual(agent.game_over([repeated] * 3), "draw")
        self.assertIsNone(agent.game_over([repeated] * 2))
        self.assertIsNone(agent.game_over([{"move": 3, "turn": "W", "board": "W" + "x" * 22}]))

    def test_finished_game_stops_without_searching(self):
        session = {"version": 1, "side": "W", "seconds": 0.05, "depth": 2,
                   "history": [{"move": 25, "turn": "W", "board": "WWxxxxxBBBxxxxxxxxxxxxx"}]}
        agent.play_session(session, self.dir / "end.json", scripted([]), self.output.append)
        text = "\n".join(self.output)
        self.assertIn("Game over: Black wins.", text)
        self.assertNotIn("Calculating", text)


if __name__ == "__main__":
    unittest.main()
