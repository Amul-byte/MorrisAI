"""Part II: ALPHA-BETA for the opening, playing White.

    python3 ABOpening.py <input board file> <output board file> <depth>

Same input and output as MiniMaxOpening.py. For the same board and depth
it chooses the same move with the same MINIMAX estimate, but it usually
evaluates fewer positions, because it skips branches that cannot change
the decision.

    alpha  the best value White is already sure of on the current path
    beta   the best value Black is already sure of on the current path

Once a position's value is outside the range alpha to beta, the player
above it will never choose it, so its remaining moves are not searched.
"""

from math import inf

from morris.board import generate_moves
from morris.cli import read_arguments, report
from morris.evaluation import baseline


class OpeningAlphaBeta:
    """ALPHA-BETA over opening placements. White maximizes, Black minimizes.

    Moves are tried in generator order, as in MiniMaxOpening.py, which is
    what makes the two programs pick the same move on a tie.
    """

    def __init__(self, estimate=baseline):
        self.estimate = estimate
        self.positions_evaluated = 0

    def best_move(self, board, depth):
        """Return (White's chosen board, its MINIMAX value)."""
        if depth == 0:
            return board, self.score(board)
        moves = generate_moves(board, "W", True)
        if not moves:
            return board, self.score(board)
        alpha, beta = -inf, inf
        best_board, best_value = moves[0], -inf
        for child in moves:
            value = self.min_value(child, depth - 1, alpha, beta)
            if value > best_value:
                best_board, best_value = child, value
            alpha = max(alpha, best_value)
        return best_board, best_value

    def max_value(self, board, depth, alpha, beta):
        """White to move: the largest value White can reach, cut off at beta."""
        if depth == 0:
            return self.score(board)
        moves = generate_moves(board, "W", True)
        if not moves:
            return self.score(board)
        value = -inf
        for child in moves:
            value = max(value, self.min_value(child, depth - 1, alpha, beta))
            if value >= beta:
                return value  # Black already has something at least as good elsewhere.
            alpha = max(alpha, value)
        return value

    def min_value(self, board, depth, alpha, beta):
        """Black to move: the smallest value Black can reach, cut off at alpha."""
        if depth == 0:
            return self.score(board)
        moves = generate_moves(board, "B", True)
        if not moves:
            return self.score(board)
        value = inf
        for child in moves:
            value = min(value, self.max_value(child, depth - 1, alpha, beta))
            if value <= alpha:
                return value  # White already has something at least as good elsewhere.
            beta = min(beta, value)
        return value

    def score(self, board):
        self.positions_evaluated += 1
        return self.estimate(board, True)


def main():
    parser, board, output, depth = read_arguments()
    search = OpeningAlphaBeta()
    best_board, value = search.best_move(board, depth)
    report(parser, output, best_board, search.positions_evaluated, value)


if __name__ == "__main__":
    main()
