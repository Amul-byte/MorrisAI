from types import SimpleNamespace

from ABGame import GameAlphaBeta
from ABOpening import OpeningAlphaBeta
from MiniMaxGame import GameMinimax
from MiniMaxOpening import OpeningMinimax
from morris.evaluation import WIN, baseline, improved


def fixed_search(board, depth, opening, *, side="W", pruning=False, enhanced=False):
    estimate = improved if enhanced else baseline
    if opening:
        search = (OpeningAlphaBeta if pruning else OpeningMinimax)(estimate=estimate)
    else:
        options = {"win_score": WIN, "judge_horizon": True} if enhanced else {}
        search = (GameAlphaBeta if pruning else GameMinimax)(estimate=estimate, **options)
    root = board.swapped() if side == "B" else board
    chosen, score = search.best_move(root, depth)
    return SimpleNamespace(board=chosen.swapped() if side == "B" else chosen,
                           score=score, evaluations=search.positions_evaluated)
