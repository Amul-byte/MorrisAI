import argparse
import os
from pathlib import Path
import tempfile

from .board import Board


def read_arguments():
    parser = argparse.ArgumentParser(description="Choose one Morris-variant move.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("depth", type=int, help="search depth in plies; at least 1")
    args = parser.parse_args()
    if args.depth < 1:
        parser.error("depth must be at least 1 to select a move")
    try:
        board = Board.parse(args.input.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        parser.error(str(error))
    return parser, board, args.output, args.depth


def report(parser, output: Path, board: Board, evaluations: int, score: int) -> None:
    try:
        write_board(output, board)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print_result(board, evaluations, score)


def write_board(path: Path, board: Board) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(str(board) + "\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def print_result(board: Board, evaluations: int, score: int) -> None:
    print(f"Board Position: {board}")
    print(f"Positions evaluated by static estimation: {evaluations}")
    print(f"MINIMAX estimate: {score}")
