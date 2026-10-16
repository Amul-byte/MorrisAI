"""Part I: MINIMAX for the midgame and endgame, playing White.

    python3 MiniMaxGame.py <input board file> <output board file> <depth>

Reads a board, picks White's best move found by MINIMAX searching <depth>
turns ahead (at least 1), writes the new board to the output file, and
prints:

    Board Position: <the new board>
    Positions evaluated by static estimation: <calls to the static estimator>
    MINIMAX estimate: <value of the chosen move>

A piece slides to an adjacent empty square. A side with exactly three
pieces hops to any empty square instead (the endgame). A move that closes
a mill also removes one opponent piece that is not in a mill. If the input
board is already a finished game, the program prints that board unchanged.
The board, the move generator, and the static estimators are shared by
every program and live in the morris/ folder.
"""

from math import inf

from morris.board import game_winner, generate_moves
from morris.cli import read_arguments, report
from morris.evaluation import baseline

HANDOUT_WIN = 10000


class GameMinimax:
    """MINIMAX over midgame and endgame moves. White maximizes, Black minimizes.

    A side loses when it has two or fewer pieces or cannot move on its turn
    (morris.board.game_winner). A game that ends before the depth limit
    scores +win_score for a White win and -win_score for a Black win.

    At the depth limit the handout's estimator is applied exactly as
    written, even to a finished game. The improved program passes
    judge_horizon=True so a finished game is recognized there as well.
    Every score adds one to positions_evaluated.
    """

    def __init__(self, estimate=baseline, win_score=HANDOUT_WIN, judge_horizon=False):
        self.estimate = estimate
        self.win_score = win_score
        self.judge_horizon = judge_horizon
        self.positions_evaluated = 0

    def best_move(self, board, depth):
        """Return (White's chosen board, its MINIMAX value)."""
        value = self.leaf_value(board, "W", depth)
        if value is not None:
            return board, value
        moves = generate_moves(board, "W", False)
        if not moves:
            return board, self.score(board)
        best_board, best_value = moves[0], -inf
        for child in moves:
            value = self.min_value(child, depth - 1)
            # Only a strictly larger value replaces the choice, so a tie keeps
            # the earlier generated move. Alpha-beta uses the same rule.
            if value > best_value:
                best_board, best_value = child, value
        return best_board, best_value

    def max_value(self, board, depth):
        """White to move: the largest value White can reach."""
        value = self.leaf_value(board, "W", depth)
        if value is not None:
            return value
        moves = generate_moves(board, "W", False)
        if not moves:
            return self.score(board)
        return max(self.min_value(child, depth - 1) for child in moves)

    def min_value(self, board, depth):
        """Black to move: the smallest value Black can reach."""
        value = self.leaf_value(board, "B", depth)
        if value is not None:
            return value
        moves = generate_moves(board, "B", False)
        if not moves:
            return self.score(board)
        return min(self.max_value(child, depth - 1) for child in moves)

    def leaf_value(self, board, turn, depth):
        """The value of a board that is not searched further, or None to keep searching."""
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
