"""MINIMAX for the midgame and endgame, playing Black: swap colors, search as White, swap back.

Usage: python3 MiniMaxGameBlack.py <input> <output> <depth>
"""

from morris.cli import read_arguments, report

from MiniMaxGame import GameMinimax


def main():
    parser, board, output, depth = read_arguments()
    search = GameMinimax()
    swapped_choice, value = search.best_move(board.swapped(), depth)
    report(parser, output, swapped_choice.swapped(), search.positions_evaluated, value)


if __name__ == "__main__":
    main()
