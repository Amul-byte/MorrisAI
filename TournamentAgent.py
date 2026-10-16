"""Tournament runner with move-number tracking and optional persistent history.

    python3 TournamentAgent.py              interactive console (new game or resume)
    python3 TournamentAgent.py input output --side W --move-number 1 [--history game.json]
"""

import argparse
from collections import Counter
from datetime import datetime
import json
import math
from pathlib import Path
import re
import sys
from uuid import uuid4

from morris.board import Board, game_winner, generate_moves, opponent
from morris.cli import print_result, write_board
from morris.history_io import write_history
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
        seen = validate_log(entries)
        last = entries[-1]
        if last == current:
            return entries
        if seen[(last["board"], last["turn"])] >= 3:
            raise ValueError("History already ends in a threefold-repetition draw")
        validate_transition(last, current)
    entries.append(current)
    return entries


def validate_log(entries) -> Counter:
    """Check every entry and step of a game log; return how often each state occurred."""
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
    return seen


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


SESSION_DIR = Path(__file__).resolve().parent / "games"
HEADER = re.compile(r"Move\s+(\d+)\s*[-–—]\s*(White|Black)\s*:?", re.IGNORECASE)
NAMES = {"W": "White", "B": "Black"}
POSTING_MARGIN = 180  # Above this, less than a minute of the 4 minutes is left to post.
START = {"move": 1, "turn": "W", "board": "x" * 23}


def format_board(board: str) -> str:
    c = board
    return "\n".join([
        f"6  {c[20]}--------{c[21]}--------{c[22]}",
        "   | \\      |      / |",
        f"5  |  {c[17]}-----{c[18]}-----{c[19]}  |",
        "   |  | \\   |   / |  |",
        f"4  |  |  {c[14]}--{c[15]}--{c[16]}  |  |",
        "   |  |  |     |  |  |",
        f"3  {c[8]}--{c[9]}--{c[10]}     {c[11]}--{c[12]}--{c[13]}",
        "   |  |  |     |  |  |",
        f"2  |  |  {c[6]}-----{c[7]}  |  |",
        "   |  | /       \\ |  |",
        f"1  |  {c[3]}-----{c[4]}-----{c[5]}  |",
        "   | /      |      \\ |",
        f"0  {c[0]}--------{c[1]}--------{c[2]}",
        "   a  b  c  d  e  f  g",
    ])


def check_settings(seconds, depth) -> None:
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 < seconds <= 210:
        raise ValueError("Search time must be greater than 0 and at most 210 seconds")
    if type(depth) is not int or not 1 <= depth <= 100:
        raise ValueError("Maximum depth must be between 1 and 100 plies")


def time_warning(seconds: float) -> str | None:
    if seconds > POSTING_MARGIN:
        return (f"Warning: a {seconds:g}s search leaves less than a minute to paste and post "
                f"within the 4 minutes after the opponent posts.")
    return None


def load_session(path: Path) -> dict:
    session = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(session, dict) or session.get("version") != 1:
        raise ValueError("Choose a session file created by this console")
    if session.get("side") not in NAMES:
        raise ValueError("Saved session has an invalid side")
    check_settings(session.get("seconds"), session.get("depth"))
    validate_log(session.get("history"))
    if session["history"][0] != START:
        raise ValueError("Saved session does not start from the empty board")
    return session


def game_over(entries: list[dict]) -> str | None:
    """'W' or 'B' for a win, 'draw' for threefold repetition, None while the game goes on."""
    last = entries[-1]
    if last["move"] > 18:
        winner = game_winner(Board.parse(last["board"]), last["turn"])
        if winner:
            return winner
    seen = Counter((e["board"], e["turn"]) for e in entries)
    return "draw" if seen[(last["board"], last["turn"])] >= 3 else None


def teams_message(entries: list[dict]) -> str:
    """The last entry is the position after a move, so the mover is the other side."""
    last = entries[-1]
    return f"Move {last['move'] - 1} - {NAMES[opponent(last['turn'])]}\n{last['board']}"


def parse_opponent(text: str, state: dict) -> Board | None:
    """Accept a board alone, a Teams header alone, or a header and board on one line."""
    header = HEADER.match(text)
    if header:
        number, name = header.groups()
        expected = f"Move {state['move']} - {NAMES[state['turn']]}"
        if int(number) != state["move"] or name.title() != NAMES[state["turn"]]:
            raise ValueError(f"Expected {expected}.")
        text = text[header.end():].strip()
        if not text:
            return None  # A two-line paste sends the board on the next line.
    text = text.strip("\"'` ").translate(str.maketrans("wbX", "WBx"))
    return Board.parse(text)


def play_session(session: dict, path: Path, read=input, write=print) -> None:
    side = session["side"]
    write(f"\nYou are {NAMES[side]}. Saved session: {path}")
    write("Paste the opponent's board and press Enter. Commands: show, time N, depth N, quit.")
    write("Ctrl-C during a search stops it and keeps the deepest completed result.")
    write("This console never posts online; copy the Teams message yourself.")
    entries = session["history"]
    if len(entries) > 1 and entries[-1]["turn"] != side:
        write("\nLast saved move from your team (do not post it twice):\n" + teams_message(entries))

    while True:
        entries = session["history"]
        state = entries[-1]
        result = game_over(entries)
        if result:
            write("\nGame over: draw by threefold repetition." if result == "draw"
                  else f"\nGame over: {NAMES[result]} wins.")
            write(f"Full game saved: {path}")
            return

        board, move = Board.parse(state["board"]), state["move"]
        if state["turn"] == side:
            phase = "opening" if move <= 18 else "midgame"
            write(f"\nCalculating Move {move} - {NAMES[side]} ({phase}), "
                  f"up to {session['seconds']:g}s and depth {session['depth']}...")
            history = [(Board.parse(e["board"]), e["turn"]) for e in entries[:-1]]
            found = TournamentSearch().choose(board, side, max(0, 19 - move),
                                              time_limit=session["seconds"],
                                              max_depth=session["depth"], history=history)
            if found.board not in generate_moves(board, side, move <= 18):
                raise ValueError("Agent returned an illegal move; nothing was recorded")
            session["history"] = entries + [{"move": move + 1, "turn": opponent(side),
                                             "board": str(found.board)}]
            write_history(path, session)
            write(f"Completed depth: {found.depth}; elapsed: {found.elapsed:.2f}s; "
                  f"positions evaluated: {found.evaluations}; score: {found.score}")
            if found.depth == 0:
                write("No search depth completed; this is the first legal move as a fallback.")
            write("\nCOPY THESE TWO LINES INTO TEAMS:\n" + teams_message(session["history"]) + "\n")
            continue

        text = read(f"Opponent Move {move} - {NAMES[state['turn']]}> ").strip()
        command = text.lower()
        if not text:
            continue
        if command in ("quit", "exit", "q"):
            write(f"Session saved. Resume with: {path}")
            return
        if command == "show":
            write(format_board(state["board"]))
            if len(entries) > 1:
                write("Last recorded move:\n" + teams_message(entries))
            continue
        if command.split()[0] in ("time", "depth"):
            try:
                name, value = command.split()
                seconds = float(value) if name == "time" else session["seconds"]
                depth = int(value) if name == "depth" else session["depth"]
                check_settings(seconds, depth)
            except ValueError:
                write("Use time N (0 < N <= 210 seconds) or depth N (1 to 100). Settings unchanged.")
                continue
            session.update(seconds=seconds, depth=depth)
            write_history(path, session)
            write(f"Next searches: up to {seconds:g}s and depth {depth}.")
            if time_warning(seconds):
                write(time_warning(seconds))
            continue
        try:
            reply = parse_opponent(text, state)
            if reply is None:
                continue
            if reply == board:
                raise ValueError("That is the current board, not a new move.")
            validate_transition(state, {"move": move + 1, "turn": opponent(state["turn"]),
                                        "board": str(reply)})
        except ValueError as error:
            write(f"Invalid input: {error} Game unchanged; paste again.")
            continue
        # Saved before searching, so a resumed session continues from this position.
        session["history"] = entries + [{"move": move + 1, "turn": opponent(state["turn"]),
                                         "board": str(reply)}]
        write_history(path, session)
        write("Opponent move is valid.")


def ask(prompt: str, convert, valid, default=None, read=input, write=print):
    while True:
        text = read(prompt).strip()
        if not text and default is not None:
            return default
        try:
            value = convert(text)
            if valid(value):
                return value
        except ValueError:
            pass
        write("Please enter one of the allowed values.")


def run_console(read=input, write=print, session_dir: Path = SESSION_DIR) -> int:
    """Start or resume a game in the terminal. Returns the exit code."""
    path = None
    try:
        write("MORRIS TOURNAMENT CONSOLE")
        mode = ask("New game or resume? [new/resume, Enter=new]: ", str.lower,
                   lambda s: s in ("new", "resume"), "new", read, write)
        if mode == "resume":
            path = Path(read("Paste the saved session JSON path: ").strip().strip("\"'")).expanduser()
            path = path.resolve()
            session = load_session(path)
        else:
            color = ask("Your color [white/black]: ", str.lower,
                        lambda s: s in ("white", "black", "w", "b"), read=read, write=write)
            side = color[0].upper()
            seconds = ask("Search seconds [Enter=180; use 2 for practice]: ", float,
                          lambda n: math.isfinite(n) and 0 < n <= 210, 180.0, read, write)
            depth = ask("Maximum depth [1..100, Enter=64]: ", int,
                        lambda n: 1 <= n <= 100, 64, read, write)
            session_dir.mkdir(parents=True, exist_ok=True)
            name = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:6]
            path = session_dir / f"{name}-{NAMES[side].lower()}.json"
            session = {"version": 1, "side": side, "seconds": seconds, "depth": depth,
                       "history": [dict(START)]}
            write_history(path, session)
        if time_warning(session["seconds"]):
            write(time_warning(session["seconds"]))
        play_session(session, path, read, write)
        return 0
    except (KeyboardInterrupt, EOFError):
        write("\nStopped. Accepted moves are already saved.")
        if path is not None:
            write(f"Resume with: {path}")
        return 0
    except (ValueError, OSError, TypeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        if path is not None:
            print(f"Session file: {path}", file=sys.stderr)
        return 2


def main() -> None:
    if len(sys.argv) == 1:
        sys.exit(run_console())
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
