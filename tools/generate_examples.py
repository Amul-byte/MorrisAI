"""Rewrite Examples.txt from real runs of the assignment programs.

    python3 -m tools.generate_examples

Every printed result comes from running the program on a file in assets/.
The script stops if alpha-beta no longer matches MINIMAX, if the improved
estimator no longer picks a different move, or if MyStaticEstimation.txt
quotes a move the programs no longer choose.
"""

from pathlib import Path
import subprocess
import sys
import tempfile

from morris.board import COORDINATES, Board
from morris.evaluation import features

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ("pieces", "mills", "threats", "forks", "mobility", "blocked", "connections")
POSITION_1 = "handout_position_1"
POSITION_2 = "handout_position_2"

PART_II = [
    ("opening", POSITION_1, "MiniMaxOpening", "ABOpening"),
    ("midgame", POSITION_2, "MiniMaxGame", "ABGame"),
]
PART_IV = [
    ("opening", POSITION_2, "MiniMaxOpening", "MiniMaxOpeningImproved",
     "Both moves close a mill and remove the same Black piece, so the original function "
     "gives them the same score and keeps the first one, d0. The improved function prefers "
     "a6, which lies on three mill lines, over d0, which lies on one. After the move, White's "
     "connection advantage is 7 instead of 5, White has 2 more free neighboring squares than "
     "Black instead of an equal number, and one blocked piece more than Black instead of two. "
     "The search also checked Black's reply at depth 2."),
    ("midgame", POSITION_2, "MiniMaxGame", "MiniMaxGameImproved",
     "It slides b1 to d1. From d1 the piece can slide on to d0 and close a0-d0-g0, and a0 or "
     "b3 can slide into b1 and close b1-d1-f1, so White has two different mill-closing squares "
     "instead of one: the threat difference becomes +2 instead of +1. Black would need two "
     "moves to cover both. The price is that White's a0-b1-c2 mill is open for now (mills -1 "
     "instead of 0) and its mobility lead is +2 instead of +3. The original move, a3 to a6, blocks Black's "
     "c4-b5-a6 line and leaves Black 5 moves instead of 6, which is the only thing besides "
     "material that the original midgame function measures."),
]


def run(program, board_name, depth):
    """Return the command and the three lines the program printed."""
    with tempfile.TemporaryDirectory() as temp:
        result = subprocess.run(
            [sys.executable, program + ".py", f"assets/{board_name}.txt",
             str(Path(temp) / "board2.txt"), str(depth)],
            cwd=ROOT, capture_output=True, text=True, check=True)
    lines = result.stdout.splitlines()
    command = f"$ python3 {program}.py assets/{board_name}.txt board2.txt {depth}"
    return command, lines


def chosen(lines):
    return lines[0].removeprefix("Board Position: ")


def evaluated(lines):
    return int(lines[1].rsplit(":", 1)[1])


def estimate(lines):
    return int(lines[2].rsplit(":", 1)[1])


def describe_move(before, after, phase):
    """Plain-English description of White's move."""
    gone = [COORDINATES[i] for i in range(23) if before[i] == "W" and after[i] != "W"]
    new = [COORDINATES[i] for i in range(23) if after[i] == "W" and before[i] != "W"]
    captured = [COORDINATES[i] for i in range(23) if before[i] == "B" and after[i] != "B"]
    text = f"White places a piece at {new[0]}" if phase == "opening" else f"White moves {gone[0]} to {new[0]}"
    if captured:
        text += f" and removes the Black piece at {captured[0]}"
    return text


def feature_difference(board_text, phase):
    board = Board.parse(board_text)
    opening = phase == "opening"
    white = features(board.white, board.black, opening)
    black = features(board.black, board.white, opening)
    return dict(zip(FEATURES, (w - b for w, b in zip(white, black))))


def main():
    boards = {name: (ROOT / "assets" / f"{name}.txt").read_text().strip()
              for name in (POSITION_1, POSITION_2)}
    out = [
        "Morris AI - Team 7",
        "",
        "This file answers two requirements of the project handout:",
        "  Part II: at least two cases where ALPHA-BETA evaluates fewer positions than MINIMAX,",
        "           with the same MINIMAX estimate and the same move.",
        "  Part IV: at least two board positions where the improved static estimation selects",
        "           a different move than the original one, with a reason for preferring it.",
        "",
        "Each case shows the exact command and the three lines the submitted program printed.",
        "Input files, in the assets/ folder, are the two positions drawn in the Morris Variant handout:",
        f"  assets/{POSITION_1}.txt = {boards[POSITION_1]}",
        f"  assets/{POSITION_2}.txt = {boards[POSITION_2]}",
        'Depth counts individual turns (plies). "Positions evaluated" counts calls to the static estimator.',
        "",
        "",
        "PART II: ALPHA-BETA EVALUATES FEWER POSITIONS THAN MINIMAX",
        "",
    ]
    for number, (phase, name, minimax, alphabeta) in enumerate(PART_II, 1):
        plain_command, plain = run(minimax, name, 3)
        pruned_command, pruned = run(alphabeta, name, 3)
        assert (chosen(plain), estimate(plain)) == (chosen(pruned), estimate(pruned))
        assert evaluated(pruned) < evaluated(plain)
        saved = round(100 * (1 - evaluated(pruned) / evaluated(plain)))
        out += [f"Case {number} ({phase}, depth 3)", f"Input board: {boards[name]}", "",
                "MINIMAX:", "  " + plain_command, *("  " + line for line in plain), "",
                "ALPHA-BETA:", "  " + pruned_command, *("  " + line for line in pruned), "",
                f"Selected move: {describe_move(boards[name], chosen(plain), phase)}",
                f"Same move and same MINIMAX estimate ({estimate(plain)}). Alpha-beta evaluated "
                f"{evaluated(pruned)} positions instead of {evaluated(plain)} ({saved}% fewer).",
                "Alpha-beta stops exploring a branch once it cannot change the decision above it.",
                "Both searches try moves in the same order and keep the first move on a tie.", ""]
    out += ["", "PART IV: IMPROVED STATIC ESTIMATION SELECTS A DIFFERENT MOVE",
            "Scores from the two estimators use different scales. We compare the chosen moves, not the numbers.",
            ""]
    quoted = (ROOT / "MyStaticEstimation.txt").read_text()
    for number, (phase, name, original, improved, reason) in enumerate(PART_IV, 1):
        original_command, before = run(original, name, 2)
        improved_command, after = run(improved, name, 2)
        assert chosen(before) != chosen(after)
        for line in (chosen(before), chosen(after)):
            if line not in quoted:
                raise SystemExit(f"MyStaticEstimation.txt does not quote the chosen board {line}")
        out += [f"Case {number} ({phase}, depth 2)", f"Input board: {boards[name]}", "",
                "ORIGINAL ESTIMATION:", "  " + original_command, *("  " + line for line in before),
                f"  Move: {describe_move(boards[name], chosen(before), phase)}", "",
                "IMPROVED ESTIMATION:", "  " + improved_command, *("  " + line for line in after),
                f"  Move: {describe_move(boards[name], chosen(after), phase)}", "",
                "Feature differences after each move (White minus Black):",
                f"  original move: {feature_difference(chosen(before), phase)}",
                f"  improved move: {feature_difference(chosen(after), phase)}", "",
                f"Why we prefer the improved move: {reason}", ""]
    (ROOT / "Examples.txt").write_text("\n".join(out).rstrip() + "\n")
    print("Wrote Examples.txt")


if __name__ == "__main__":
    main()
