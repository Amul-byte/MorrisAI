"""Part IV: MINIMAX for the opening with the improved static estimator, playing White.

    python3 MiniMaxOpeningImproved.py <input board file> <output board file> <depth>

Same input, output, and search as MiniMaxOpening.py. The only change is
the function that scores a position: improved() in morris/evaluation.py,
explained in MyStaticEstimation.txt.
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
