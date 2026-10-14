"""Reference full-width MINIMAX and equivalent ALPHA-BETA pruning."""

from dataclasses import dataclass

from .board import Board, game_winner, generate_moves, opponent
from .evaluation import WIN, baseline, improved

INF = 10**12


@dataclass(slots=True)
class SearchResult:
    board: Board
    score: int
    evaluations: int
    nodes: int
    depth: int
    elapsed: float = 0.0
    timed_out: bool = False


def fixed_search(board: Board, depth: int, opening: bool, *, side: str = "W",
                 pruning: bool = False, enhanced: bool = False) -> SearchResult:
    """Depth is plies. Ties always choose the first generated successor.

    Black assignment programs use the handout's color-swap method, so their
    reported estimate is from Black's perspective. Opening entry points keep
    the opening generator at every ply, as required by the phase-only API.
    """
    if depth < 0:
        raise ValueError("Search depth must be nonnegative")
    opponent(side)  # validate even for a depth-zero call
    root = board.swapped() if side == "B" else board
    evaluate = improved if enhanced else baseline
    evaluations = nodes = 0

    def visit(position: Board, remaining: int, turn: str,
              alpha: int, beta: int) -> tuple[int, Board]:
        nonlocal evaluations, nodes
        nodes += 1
        if enhanced and not opening:
            winner = game_winner(position, turn)
            if winner is not None:
                evaluations += 1
                return WIN * (1 if winner == "W" else -1), position
        if remaining == 0:
            evaluations += 1
            return evaluate(position, opening), position
        if not opening:
            winner = game_winner(position, turn)
            if winner is not None:
                evaluations += 1
                # The literal estimator intentionally lacks White-blocked
                # detection; adjudicate that true terminal here.
                value = (WIN if enhanced else 10000) * (1 if winner == "W" else -1)
                return value, position
        moves = generate_moves(position, turn, opening)
        if not moves:
            evaluations += 1
            return evaluate(position, opening), position
        best, chosen = (-INF if turn == "W" else INF), moves[0]
        for child in moves:
            value, _ = visit(child, remaining - 1, opponent(turn), alpha, beta)
            if (turn == "W" and value > best) or (turn == "B" and value < best):
                best, chosen = value, child
            if pruning:
                if turn == "W":
                    alpha = max(alpha, best)
                else:
                    beta = min(beta, best)
                if alpha >= beta:
                    break
        return best, chosen

    score, chosen = visit(root, depth, "W", -INF, INF)
    return SearchResult(chosen.swapped() if side == "B" else chosen, score,
                        evaluations, nodes, depth)
