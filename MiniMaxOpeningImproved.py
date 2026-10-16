"""MINIMAX for the opening with the improved estimator (see MyStaticEstimation.txt).

Usage: python3 MiniMaxOpeningImproved.py <input> <output> <depth>
"""

from morris.cli import read_arguments, report
from morris.evaluation import improved

from MiniMaxOpening import OpeningMinimax


def main():
    parser, board, output, depth = read_arguments()
    search = OpeningMinimax(estimate=improved)
    best_board, value = search.best_move(board, depth)
    report(parser, output, best_board, search.positions_evaluated, value)


if __name__ == "__main__":
    main()
