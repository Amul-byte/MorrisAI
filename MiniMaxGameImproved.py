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
