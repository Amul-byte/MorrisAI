"""Tournament runner with move-number tracking and optional persistent history."""

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys

from morris.board import Board, game_winner, generate_moves, opponent
from morris.cli import print_result, write_board
from morris.tournament import TournamentSearch, position_key


def load_history(path: Path | None, board: Board, side: str, move_number: int):
    """An existing log ends at the last selected move; validate the reply.

    Each entry describes the board BEFORE the numbered move. This lets two
    operators use separate logs, or lets both programs share a single log.
    """
    current = {"move": move_number, "turn": side, "board": str(board)}
    entries = []
    if path and path.exists():
        entries = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(entries, list) or not entries:
            raise ValueError("History must be a nonempty JSON list")
        previous = None
        seen = Counter()
        for item in entries:
            if not isinstance(item, dict) or set(item) != {"move", "turn", "board"}:
                raise ValueError("History entries require move, turn, and board")
            validate_position(Board.parse(item["board"]), item["turn"], item["move"])
            if previous:
                if seen[(previous["board"], previous["turn"])] >= 3:
                    raise ValueError("History continues beyond a threefold-repetition draw")
                validate_transition(previous, item)
            seen[(item["board"], item["turn"])] += 1
            previous = item
        last = entries[-1]
        if last == current:
            return entries
        if seen[(last["board"], last["turn"])] >= 3:
            raise ValueError("History already ends in a threefold-repetition draw")
        validate_transition(last, current)
    entries.append(current)
    return entries


def validate_position(board: Board, side: str, move_number: int) -> None:
    if type(move_number) is not int or move_number < 1:
        raise ValueError("Move number must be a positive integer (White starts at 1)")
    if side != ("W" if move_number % 2 else "B"):
        raise ValueError("Side disagrees with move number: White odd, Black even")
    placed = min(move_number - 1, 18)
    if board.white.bit_count() > (placed + 1) // 2 or board.black.bit_count() > placed // 2:
        raise ValueError("Board has more pieces than could have been placed by this move")


def validate_transition(previous: dict, current: dict) -> None:
    if current["move"] != previous["move"] + 1:
        raise ValueError("History has a gap or belongs to a different game; use a fresh log")
    before, after = Board.parse(previous["board"]), Board.parse(current["board"])
    if previous["move"] > 18 and game_winner(before, previous["turn"]):
        raise ValueError("History continues after the game has ended")
    if after not in generate_moves(before, previous["turn"], previous["move"] <= 18):
        raise ValueError("The supplied position is not a legal reply to the history")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--side", choices=("W", "B"), required=True)
    parser.add_argument("--move-number", type=int, required=True,
                        help="number of the move YOU are about to make (1-based)")
    parser.add_argument("--time-limit", type=float, default=180,
                        help="search seconds, 0 < seconds <= 210; default 180")
    parser.add_argument("--max-depth", type=int, default=64)
    parser.add_argument("--history", type=Path,
                        help="JSON game log; created if absent and updated after search")
    args = parser.parse_args()
    if not math.isfinite(args.time_limit) or not 0 < args.time_limit <= 210:
        parser.error("time limit must be greater than 0 and at most 210 seconds")
    if not 1 <= args.max_depth <= 100:
        parser.error("max depth must be between 1 and 100 plies")
    try:
        paths = [args.input.resolve(), args.output.resolve()]
        if args.history:
            paths.append(args.history.resolve())
        if len(paths) != len(set(paths)):
            raise ValueError("Input, output, and history must be separate files")
        board = Board.parse(args.input.read_text(encoding="utf-8"))
        validate_position(board, args.side, args.move_number)
        entries = load_history(args.history, board, args.side, args.move_number)
        history = [(Board.parse(item["board"]), item["turn"]) for item in entries[:-1]]

        def checkpoint(result):
            write_board(args.output, result.board)
            if result.depth:
                print(f"Depth {result.depth}: score {result.score}, "
                      f"{result.nodes} nodes, {result.elapsed:.2f}s", file=sys.stderr)

        search = TournamentSearch()
        result = search.choose(board, args.side, max(0, 19 - args.move_number),
                               time_limit=args.time_limit, max_depth=args.max_depth,
                               history=history, on_complete=checkpoint)
        next_turn = opponent(args.side)
        entries.append({"move": args.move_number + 1, "turn": next_turn,
                        "board": str(result.board)})
        if args.history:
            # Use the same atomic replacement as board output, but JSON data.
            from morris.history_io import write_history
            write_history(args.history, entries)
        counts = Counter(position_key(Board.parse(e["board"]), e["turn"]) for e in entries)
        if counts[position_key(result.board, next_turn)] >= 3:
            print("Selected position produces threefold repetition: draw.", file=sys.stderr)
        if not args.history or entries[0]["move"] != 1:
            print("History is incomplete; verify earlier repetitions against the game log.",
                  file=sys.stderr)
    except (OSError, ValueError, TypeError) as error:
        parser.error(str(error))
    print_result(result.board, result.evaluations, result.score)
    print(f"Completed depth: {result.depth}; elapsed: {result.elapsed:.3f}s", file=sys.stderr)
    if result.depth == 0:
        print("Used legal fallback; no search iteration completed. Estimate is a placeholder.",
              file=sys.stderr)
    print(f"\nMove {args.move_number} - {'White' if args.side == 'W' else 'Black'}")
    print(result.board)


if __name__ == "__main__":
    main()
