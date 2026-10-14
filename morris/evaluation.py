"""Prescribed estimators and an explainable, color-symmetric alternative."""

from functools import lru_cache

from .board import (Board, FULL, MILL_MASKS, MILLS_AT, NEIGHBOR_MASKS,
                    generate_moves, indices, mobility)

WIN = 1_000_000


def baseline(board: Board, opening: bool) -> int:
    """PDF p.5, verbatim formula from White's perspective."""
    white, black = board.white.bit_count(), board.black.bit_count()
    if opening:
        return white - black
    if black <= 2:
        return 10000
    if white <= 2:
        return -10000
    black_moves = len(generate_moves(board, "B", False))
    if not black_moves:
        return 10000
    return 1000 * (white - black) - black_moves


def features(own: int, other: int, opening: bool) -> tuple[int, ...]:
    """Material, mills, threats, forks, mobility, blocked, connectivity.

    A threat counts an empty destination that can ACTUALLY complete a mill.
    Moving a supporting piece out of that same mill does not count.
    """
    empty = FULL ^ (own | other)
    mills = 0
    threats = 0
    for mill in MILL_MASKS:
        held = mill & own
        if held == mill:
            mills += 1
        elif held.bit_count() == 2 and not mill & other:
            vacancy = mill & empty
            if opening:
                threats |= vacancy
            else:
                dst = vacancy.bit_length() - 1
                sources = own & ~mill
                if own.bit_count() == 3 or sources & NEIGHBOR_MASKS[dst]:
                    threats |= vacancy
    # A placement creating threats on two distinct squares cannot be blocked
    # by a single placement. Count opportunities, not impossible double captures.
    forks = 0
    if opening:
        for dst in indices(empty):
            remaining = 0
            for mill in MILLS_AT[dst]:
                if not mill & other and (mill & own).bit_count() == 1:
                    remaining |= mill & empty & ~(1 << dst)
            if remaining.bit_count() >= 2:
                forks += 1
    blocked = sum(not (NEIGHBOR_MASKS[i] & empty) for i in indices(own))
    if own.bit_count() == 3 and not opening:
        blocked = 0
    connectivity = sum(len(MILLS_AT[i]) for i in indices(own))
    available = (sum((NEIGHBOR_MASKS[i] & empty).bit_count() for i in indices(own))
                 if opening else mobility(own, empty))
    return (own.bit_count(), mills, threats.bit_count(), forks,
            available, blocked, connectivity)


OPENING_WEIGHTS = (120, 25, 45, 20, 2, -8, 4)
GAME_WEIGHTS = (1000, 75, 110, 0, 8, -35, 5)


@lru_cache(maxsize=65536)
def improved(board: Board, opening: bool) -> int:
    if not opening:
        if board.black.bit_count() <= 2:
            return WIN
        if board.white.bit_count() <= 2:
            return -WIN
    weights = OPENING_WEIGHTS if opening else GAME_WEIGHTS
    white = features(board.white, board.black, opening)
    black = features(board.black, board.white, opening)
    return sum(weight * (w - b) for weight, w, b in zip(weights, white, black))
