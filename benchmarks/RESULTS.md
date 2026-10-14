# Validation and local practice results

These are local development results, not official tournament matches. The
implementation was tested against the supplied handout rather than a different
online Morris ruleset. Raw results record Python/platform information.

## Paired practice games

Each pair uses the same six seeded legal opening moves. The improved agent plays
White in one game and Black in the other. Both agents use the same tournament
search engine; only the static estimator changes. Seeds are 4346–4349. Wins use
the exact variant's terminal rules; draws require threefold repetition. A game
reaching the 140-ply cap would be reported as unfinished, never as a draw.

| Experiment | Improved wins | Losses | Draws | Unfinished |
| --- | ---: | ---: | ---: | ---: |
| 0.03 seconds per move | 7 | 0 | 1 | 0 |
| Fixed depth 3, 2-second safety cap | 5 | 2 | 1 | 0 |

The fixed-depth run finished every requested iteration unless a forced result
was found earlier; its slowest search was under 0.04 seconds. In the timed run,
the largest measured search duration was 0.0377 seconds. Tiny wall-clock budgets
are sensitive to scheduling and machine load; reruns can choose different moves.

Reproduce with:

```sh
python3 -m tools.benchmark --pairs 4 --seconds 0.03 --output benchmarks/timed-practice.json
python3 -m tools.benchmark --pairs 4 --seconds 2 --depth 3 --output benchmarks/depth-three-practice.json
```

The experiment supports the improved evaluation over this baseline on these
starts. It does not prove optimal weights, dominance over other teams, or the
same win rate at the full tournament budget. The fixed-depth losses are retained
in the report. No tuning against hidden opponents or official games was done.

## Search efficiency

Cold static caches, iterative deepening through depth 6, same ordering and
evaluation; transposition bounds are the only changed setting:

| Position | Nodes without table | Nodes with table | Reduction |
| --- | ---: | ---: | ---: |
| Empty opening | 57,440 | 29,678 | 48.3% |
| First handout game position | 6,386 | 3,150 | 50.7% |

Both configurations return the same score. Run `python3 -m tools.measure_search`
for current timings and the machine-readable `search-performance.json` report.
Exact timing is machine-dependent.

## Correctness evidence

`python3 -m unittest discover -s tests -v` exercises the independent string-based
oracle on 300 seeded arbitrary boards (both phases and colors), twelve reachable
random games, every mill and adjacency edge, all eight assignment CLIs, and
search/terminal/repetition/deadline edge cases. Optimized tournament values are
also checked against exhaustive full-width search, including placement-to-game
transitions and histories approaching a draw.

The required canonical alpha-beta examples preserve MINIMAX's move and estimate:
10,626 to 504 leaf evaluations in the empty opening at depth 3, and 677 to 233
on the first handout game board at depth 3. See `Examples.txt`.
