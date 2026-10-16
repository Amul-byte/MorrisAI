"""Part I: MINIMAX for the opening, playing White.

    python3 MiniMaxOpening.py <input board file> <output board file> <depth>

Reads a board, picks White's best placement found by MINIMAX searching
<depth> turns ahead (at least 1), writes the new board to the output file,
and prints:

    Board Position: <the new board>
    Positions evaluated by static estimation: <calls to the static estimator>
    MINIMAX estimate: <value of the chosen move>

In the opening a move places one piece on an empty square. A placement
that closes a mill also removes one opponent piece that is not in a mill.
The opening generator is used at every level of the search, because the
command line gives the phase but not how many pieces are still to place.
The board, the move generator, and the static estimators are shared by
every program and live in the morris/ folder.
"""

from math import inf

from morris.board import generate_moves
from morris.cli import read_arguments, report
from morris.evaluation import baseline


class OpeningMinimax:
    """MINIMAX over opening placements. White maximizes, Black minimizes.

    A position is scored by the static estimator when the search depth runs
    out or when the side to move has no empty square left. Each of those
    scores adds one to positions_evaluated.
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
        if depth == 0:
            return self.score(board)
        moves = generate_moves(board, "W", True)
        if not moves:
            return self.score(board)
        return max(self.min_value(child, depth - 1) for child in moves)

    def min_value(self, board, depth):
        """Black to move: the smallest value Black can reach."""
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
