LABELS = "a0 d0 g0 b1 d1 f1 c2 e2 a3 b3 c3 e3 f3 g3 c4 d4 e4 b5 d5 f5 a6 d6 g6".split()
LINES = [line.split() for line in (
    "a0 d0 g0", "b1 d1 f1", "c2 e2", "a3 b3 c3", "e3 f3 g3",
    "c4 d4 e4", "b5 d5 f5", "a6 d6 g6", "a0 a3 a6", "b1 b3 b5",
    "c2 c3 c4", "e2 e3 e4", "f1 f3 f5", "g0 g3 g6", "d0 d1",
    "d4 d5 d6", "a0 b1 c2", "g0 f1 e2", "a6 b5 c4", "g6 f5 e4",
)]
LINES = [tuple(LABELS.index(label) for label in line) for line in LINES]
TRIPLES = [line for line in LINES if len(line) == 3]
ADJACENT = [set() for _ in LABELS]
for line in LINES:
    for left, right in zip(line, line[1:]):
        ADJACENT[left].add(right)
        ADJACENT[right].add(left)


def mill(board, index):
    return board[index] != "x" and any(
        index in triple and all(board[j] == board[index] for j in triple)
        for triple in TRIPLES)


def moves(board, side, opening):
    other = "B" if side == "W" else "W"
    result = []
    sources = [None] if opening else [i for i, c in enumerate(board) if c == side]
    for source in sources:
        if opening or board.count(side) == 3:
            destinations = range(23)
        else:
            destinations = [0, 4, 2] if source == 1 else sorted(ADJACENT[source])
        for destination in destinations:
            if board[destination] != "x":
                continue
            child = list(board)
            if source is not None:
                child[source] = "x"
            child[destination] = side
            captures = [i for i, c in enumerate(child) if c == other and not mill(child, i)]
            if mill(child, destination) and captures:
                for capture in captures:
                    after = child.copy()
                    after[capture] = "x"
                    result.append("".join(after))
            else:
                result.append("".join(child))
    return result


def baseline(board, opening):
    if opening:
        return board.count("W") - board.count("B")
    if board.count("B") <= 2:
        return 10000
    if board.count("W") <= 2:
        return -10000
    n = len(moves(board, "B", False))
    return 10000 if n == 0 else 1000 * (board.count("W") - board.count("B")) - n


def winner(board, turn):
    other = "B" if turn == "W" else "W"
    if board.count(turn) <= 2:
        return other
    if board.count(other) <= 2:
        return turn
    if not moves(board, turn, False):
        return other
    return None


def minimax(board, depth, opening, turn="W"):
    if depth == 0:
        return baseline(board, opening), board, 1
    won = None if opening else winner(board, turn)
    if won:
        return (10000 if won == "W" else -10000), board, 1
    children = moves(board, turn, opening)
    if not children:
        return baseline(board, opening), board, 1
    values = [minimax(child, depth - 1, opening, "B" if turn == "W" else "W")
              for child in children]
    score = (max if turn == "W" else min)(v[0] for v in values)
    index = next(i for i, value in enumerate(values) if value[0] == score)
    return score, children[index], sum(v[2] for v in values)
