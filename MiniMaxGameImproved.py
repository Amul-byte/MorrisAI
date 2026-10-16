"""Part IV: MINIMAX for the midgame and endgame with the improved static estimator, playing White.

    python3 MiniMaxGameImproved.py <input board file> <output board file> <depth>

Same input, output, and search as MiniMaxGame.py, with two changes:

  - positions are scored by improved() in morris/evaluation.py,
    explained in MyStaticEstimation.txt;
  - a finished game is recognized at the depth limit too, and scores
    +/-1000000 (WIN), so no positional score can outrank a real result.
"""

from morris.cli import read_arguments, report
from morris.evaluation import WIN, improved

from MiniMaxGame import GameMinimax


def main():
    parser, board, output, depth = read_arguments()
    search = GameMinimax(estimate=improved, win_score=WIN, judge_horizon=True)
    best_board, value = search.best_move(board, depth)
    report(parser, output, best_board, search.positions_evaluated, value)


if __name__ == "__main__":
    main()
