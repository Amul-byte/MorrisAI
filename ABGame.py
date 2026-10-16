"""Part II: ALPHA-BETA for the midgame and endgame, playing White.

    python3 ABGame.py <input board file> <output board file> <depth>

Same input and output as MiniMaxGame.py. For the same board and depth it
chooses the same move with the same MINIMAX estimate, but it usually
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

from MiniMaxGame import GameMinimax


class GameAlphaBeta(GameMinimax):
    """ALPHA-BETA over midgame and endgame moves. White maximizes, Black minimizes.

    The end-of-game rules and scores are the ones in MiniMaxGame.py. Moves
    are tried in the same generator order, which is what makes the two
    programs pick the same move on a tie.
    """

    def best_move(self, board, depth):
        """Return (White's chosen board, its MINIMAX value)."""
        value = self.leaf_value(board, "W", depth)
        if value is not None:
            return board, value
        moves = generate_moves(board, "W", False)
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
        value = self.leaf_value(board, "W", depth)
        if value is not None:
            return value
        moves = generate_moves(board, "W", False)
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
        value = self.leaf_value(board, "B", depth)
        if value is not None:
            return value
        moves = generate_moves(board, "B", False)
        if not moves:
            return self.score(board)
        value = inf
        for child in moves:
            value = min(value, self.max_value(child, depth - 1, alpha, beta))
            if value <= alpha:
                return value  # White already has something at least as good elsewhere.
            beta = min(beta, value)
        return value


def main():
    parser, board, output, depth = read_arguments()
    search = GameAlphaBeta()
    best_board, value = search.best_move(board, depth)
    report(parser, output, best_board, search.positions_evaluated, value)


if __name__ == "__main__":
    main()
