from math import inf

from morris.board import generate_moves
from morris.cli import read_arguments, report
from morris.evaluation import baseline


class OpeningMinimax:
    def __init__(self, estimate=baseline):
        self.estimate = estimate
        self.positions_evaluated = 0

    def best_move(self, board, depth):
        if depth == 0:
            return board, self.score(board)
        moves = generate_moves(board, "W", True)
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
        if depth == 0:
            return self.score(board)
        moves = generate_moves(board, "W", True)
        if not moves:
            return self.score(board)
        return max(self.min_value(child, depth - 1) for child in moves)

    def min_value(self, board, depth):
        if depth == 0:
            return self.score(board)
        moves = generate_moves(board, "B", True)
        if not moves:
            return self.score(board)
        return min(self.max_value(child, depth - 1) for child in moves)

    def score(self, board):
        self.positions_evaluated += 1
        return self.estimate(board, True)


def main():
    parser, board, output, depth = read_arguments()
    search = OpeningMinimax()
    best_board, value = search.best_move(board, depth)
    report(parser, output, best_board, search.positions_evaluated, value)


if __name__ == "__main__":
    main()
