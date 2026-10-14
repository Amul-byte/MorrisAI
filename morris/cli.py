"""Shared assignment interface and atomic board-file output."""

import argparse
import os
from pathlib import Path
import tempfile

from .board import Board
from .search import SearchResult, fixed_search


def write_board(path: Path, board: Board) -> None:
    """Readers see either the old complete board or the new complete board."""
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(str(board) + "\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def print_result(result: SearchResult) -> None:
    print(f"Board Position: {result.board}")
    print(f"Positions evaluated by static estimation: {result.evaluations}")
    print(f"MINIMAX estimate: {result.score}")


def assignment_main(*, opening: bool, pruning: bool = False,
                    side: str = "W", enhanced: bool = False) -> None:
    parser = argparse.ArgumentParser(description="Choose one Morris-variant move.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("depth", type=int, help="search depth in plies; at least 1")
    args = parser.parse_args()
    if args.depth < 1:
        parser.error("depth must be at least 1 to select a move")
    try:
        board = Board.parse(args.input.read_text(encoding="utf-8"))
        result = fixed_search(board, args.depth, opening, side=side,
                              pruning=pruning, enhanced=enhanced)
        write_board(args.output, result.board)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print_result(result)
