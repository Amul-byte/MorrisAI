from math import inf

from morris.board import game_winner, generate_moves
from morris.cli import read_arguments, report
from morris.evaluation import baseline

HANDOUT_WIN = 10000


class GameMinimax:
    def __init__(self, estimate=baseline, win_score=HANDOUT_WIN, judge_horizon=False):
        self.estimate = estimate
        self.win_score = win_score
        self.judge_horizon = judge_horizon
        self.positions_evaluated = 0

    def best_move(self, board, depth):
        value = self.leaf_value(board, "W", depth)
        if value is not None:
            return board, value
        moves = generate_moves(board, "W", False)
        if not moves:
            return board, self.score(board)
        best_board, best_value = moves[0], -inf
        for child in moves:
            value = self.min_value(child, depth - 1)
            # Strictly greater, so a tie keeps the earlier move.
            if value > best_value:
                best_board, best_value = child, value
        return best_board, best_value

    def max_value(self, board, depth):
        value = self.leaf_value(board, "W", depth)
        if value is not None:
            return value
        moves = generate_moves(board, "W", False)
        if not moves:
            return self.score(board)
        return max(self.min_value(child, depth - 1) for child in moves)

    def min_value(self, board, depth):
        value = self.leaf_value(board, "B", depth)
        if value is not None:
            return value
        moves = generate_moves(board, "B", False)
        if not moves:
            return self.score(board)
        return min(self.max_value(child, depth - 1) for child in moves)

    def leaf_value(self, board, turn, depth):
        if self.judge_horizon:
            winner = game_winner(board, turn)
            if winner:
                return self.finished(winner)
        if depth == 0:
            return self.score(board)
        winner = game_winner(board, turn)
        if winner:
            return self.finished(winner)
        return None

    def finished(self, winner):
        self.positions_evaluated += 1
        return self.win_score if winner == "W" else -self.win_score

    def score(self, board):
        self.positions_evaluated += 1
        return self.estimate(board, False)


def main():
    parser, board, output, depth = read_arguments()
    search = GameMinimax()
    best_board, value = search.best_move(board, depth)
    report(parser, output, best_board, search.positions_evaluated, value)


if __name__ == "__main__":
    main()
