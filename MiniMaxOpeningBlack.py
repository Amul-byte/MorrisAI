"""MINIMAX for the opening, playing Black: swap colors, search as White, swap back.

Usage: python3 MiniMaxOpeningBlack.py <input> <output> <depth>
"""

from morris.cli import read_arguments, report

from MiniMaxOpening import OpeningMinimax


def main():
    parser, board, output, depth = read_arguments()
    search = OpeningMinimax()
    swapped_choice, value = search.best_move(board.swapped(), depth)
    report(parser, output, swapped_choice.swapped(), search.positions_evaluated, value)


if __name__ == "__main__":
    main()
