# Morris AI Tournament

A dependency-free Python implementation of the exact **23-position variant** in
`Morris-Variant.pdf` and all programs required by `project.md`. Requires Python
3.10 or newer. Run commands from this directory; no installation is needed.

## Assignment programs

```sh
python3 MiniMaxOpening.py tests/fixtures/opening.txt board2.txt 3
python3 MiniMaxGame.py tests/fixtures/handout-game.txt board2.txt 3
python3 ABOpening.py tests/fixtures/opening.txt board2.txt 3
python3 ABGame.py tests/fixtures/handout-game.txt board2.txt 3
python3 MiniMaxOpeningBlack.py tests/fixtures/opening.txt board2.txt 3
python3 MiniMaxGameBlack.py tests/fixtures/handout-game.txt board2.txt 3
python3 MiniMaxOpeningImproved.py tests/fixtures/opening.txt board2.txt 3
python3 MiniMaxGameImproved.py tests/fixtures/handout-game.txt board2.txt 3
```

Every program accepts `input output depth`. Input and output contain one
23-character board using `W`, `B`, and lowercase `x`; a trailing newline is fine.
Depth counts individual player turns (plies), and must be at least 1. Output:

```text
Board Position: <selected 23-character board>
Positions evaluated by static estimation: <leaf evaluations>
MINIMAX estimate: <score>
```

The Black programs swap colors internally and report scores from Black's
perspective. Opening assignment scripts use the opening generator throughout
the search because this interface does not supply placement history. Game
scripts switch between sliding and hopping separately for each player. Exact
ties choose the first generated move, including in the alpha-beta scripts.
On already-terminal game positions they return the input board; this is an
evaluation result, not another legal move to post.

## Running an actual game

White starts from the empty fixture. This command chooses **move 1**:

```sh
python3 TournamentAgent.py tests/fixtures/empty.txt my-move.txt \
  --side W --move-number 1 --time-limit 180 --history game-white.json
```

After the opponent posts move 2, copy its board into `opponent.txt` and run:

```sh
python3 TournamentAgent.py opponent.txt my-move.txt \
  --side W --move-number 3 --time-limit 180 --history game-white.json
```

Black starts with the opponent's first board and `--side B --move-number 2`.
Use a separate history file for every game. The move number is the move **you
are about to make**, not the number last posted. White moves on odd numbers;
Black on even numbers. Moves 1–18 are placements; move 19 starts movement.
Never infer the phase from the number of pieces remaining after captures.

The agent prints a ready-to-copy `Move N - White/Black` message. It writes a legal
fallback to `my-move.txt` immediately and replaces it after each completed search
depth. Diagnostics go to stderr. The final result is the deepest completed
iteration; an incomplete deeper iteration never replaces it. Ctrl-C during
search returns the last completed result (or the initial legal fallback).
If no iteration finishes, stderr explicitly identifies the placeholder estimate.

The default search budget is 180 seconds, reserving about one minute of the
four-minute turn for starting the program and posting the move. The largest
accepted budget is 210 seconds. Start promptly and account for the actual Teams
timestamp; a local search deadline cannot control operator delay or OS stalls.
Use `--max-depth 4 --time-limit 1` for quick practice.

History logs record board, player to move, and move number. The agent validates
opponent replies, tracks captures without losing placement counts, and detects
threefold repetition. It rejects a root that is already a win/loss or draw.
An absent history file is created; a log started midgame cannot reconstruct past
repetitions and emits a diagnostic. The initial empty position omitted when
Black begins cannot recur in a live game. Logs include the chosen move, so
advance the input to the next actual opponent reply before invoking the agent
again. On an error, fix the input/history before using an existing output file.

## Rules that matter

- The diagram contains 23 points, 18 mills, and four diagonal mills. There is
  no `d2` point and no mill on the two-point `c2–e2` edge.
- Closing a mill removes exactly one opposing piece **outside** all mills.
  PDF page 4 says to keep the moved board if no such piece exists. This
  implementation does **not** capture a protected piece when all are in mills.
- Only a side with exactly three remaining pieces may hop after opening.
- Win/loss checks apply after opening, using the side whose turn it is.
- The baseline estimator follows PDF page 5, including counting all Black
  successor boards (capture choices included). It only checks Black's mobility
  at static leaves; that asymmetry is preserved for assignment compatibility.
  Actual terminal nodes encountered before the fixed-depth horizon are
  adjudicated; improved and tournament search also adjudicate at the horizon.
- Repetition uses the board **and** side to move, as specified in `project.md`.

## How the implementation works

| File | Responsibility |
| --- | --- |
| `morris/board.py` | Bitboard representation, diagram topology, legal moves, wins |
| `morris/evaluation.py` | Literal handout estimators and documented positional features |
| `morris/search.py` | Full MINIMAX and canonical-order ALPHA-BETA |
| `morris/tournament.py` | Timed iterative deepening, alpha-beta, ordering, bounded caches |
| `morris/cli.py`, `morris/history_io.py` | Required interface and atomic file writes |
| `TournamentAgent.py` | Placement counts, game history, turn validation, posting format |
| `tests/reference.py` | Independent string-based rule/search oracle |

Tournament search stays full-width alpha-beta: no stochastic search, selective
move omissions, or learned policy. Previous best moves, captures, killer moves,
and cutoff history improve ordering. Cached static evaluations and transposition
bounds reduce repeated work. Repetition-sensitive bounds include exact occurrence
counts; history-independent bounds are used only when no position has occurred
twice and depth is at most four, where a third occurrence is impossible. Scores
are reused only at matching depth. The caches are bounded and reset per move
where appropriate. Tournament tie-breaking can differ from assignment scripts.

`MyStaticEstimation.txt` explains every feature and weight. `Examples.txt` gives
the required pruning comparisons and different-move examples. The implementation
is designed to be explainable during the project presentation.

## Verification and submission

```sh
python3 -m unittest discover -s tests -v
python3 -m tools.generate_examples
python3 -m tools.benchmark --pairs 4 --seconds 0.03
python3 -m tools.package_submission
```

Tests cover the diagram, capture exceptions, hopping, both colors, invalid input,
independent move-generation comparisons, exact search comparisons, timed fallback,
phase transitions, repetition, and all command-line programs. Practice benchmarks
use paired starting positions and alternate the improved agent's color; unfinished
games at the move cap are reported separately from draws. Historical results and
their limits are in `benchmarks/RESULTS.md`. They are not official match results.

Submit `dist/MorrisAI-submission.zip`. It includes all required scripts, examples,
evaluation rationale, **the shared `morris/` package**, and reproducibility tools.
Do not submit only the thin top-level scripts: they import the shared package.
Actual team identifiers, official matches, Teams records, and result submission
remain operational tasks described in `project.md`.
