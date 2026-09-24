# WorldQuant International Quant Championship 2026

**578th of 22,085 teams worldwide · 15th in the United States · 36 alphas submitted out of 31,448 simulations.**

📄 **[Read the writeup →](https://mpmsds123.github.io/worldquant-iqc-2026/)**

A case study of the competition run: where the alphas came from, what the scoring
function actually rewards, and five submitted alphas in full. Every number on the
page is computed from the data in `data/` at build time — nothing is asserted
from memory.

---

## What the page covers

| Section | Question it answers |
|---|---|
| Result | Where it finished, and on what field size |
| The scoring | What a submission has to clear, and the fitness identity — verified against all 36 of my own submissions rather than taken from the docs |
| Where the alphas came from | Four sources — dataset sweeps, an LLM research pipeline, systematic expansion, paper replication — and the hit rate each returned |
| The mechanism | Why the median Sharpe of my submissions fell while the score went up four-fold |
| The book | What 36 uncorrelated alphas do to drawdown that one good one cannot |
| Five alphas | Two delay-0, three delay-1, across five data families: expression, reading, statistics, PnL |

## What is and is not published

Five alphas are written up with their expressions exactly as submitted. The other
thirty-one appear only in aggregate — the funnel counts, the median/range table,
the combined PnL curve, and as unlabelled points in the turnover-vs-Sharpe
scatter. `data/submitted_alphas.json` ships their settings, statistics and
data-family tags, with `regular.code` set to `null` for everything outside the
featured five.

The ~21k candidate expressions the scanner produced are not in this repo either;
`data/search_stats.json` holds the aggregates the funnel and source charts need.

That is deliberate. The competition runs again, and publishing a working book of
expressions hands it to the next cohort.

## Rebuilding

```bash
python3 build.py
```

No dependencies beyond the standard library. It prints a summary so a bad rebuild
is obvious:

```
wrote index.html  (64,450 bytes)
  fitness identity max error 0.0049
  funnel 31,448 -> 20,959 -> 182 -> 36
  Dataset sweeps            4,618 ->  86  1.86%
  LLM research pipeline     2,212 ->  30  1.36%
  Systematic expansion     12,264 ->  59  0.48%
  Paper replication         1,865 ->   7  0.38%
  book 211.5M on 720M = 29.4%  mdd 0.164% vs single 2.61%
```

`index.html` is a single self-contained file — no external CSS, JS, fonts or
images, and pure ASCII by construction (non-ASCII characters are HTML entities in
markup and `\uXXXX` escapes in script), so it renders correctly regardless of what
charset a server declares.

```
index.html              the page
index.template.html     the page, with a /*__DATA__*/ placeholder
build.py                injects data/ into the template -> index.html
data/                   everything the page is computed from
```

## Where the data came from

Pulled from the WorldQuant BRAIN API for my own account:

| file | contents |
|---|---|
| `data/submitted_alphas.json` | all 36 submitted alphas — settings, in-sample statistics, check results, self-correlation, data-family tags; expressions for the featured five only |
| `data/portfolio_monthly.json` | month-end cumulative PnL summed across all 36 |
| `data/pnl_featured_monthly.json` | month-end cumulative PnL for the five featured alphas |
| `data/pnl_summary.json` | year-end PnL per alpha |
| `data/drawdowns.json` | worst month-end drawdown per alpha |
| `data/search_stats.json` | scanner aggregates: batch counts, distinct expressions, gate pass rates by source |

The final standing is read off the Stage 2 competition leaderboard, the US figure
with the country filter applied.

The simulation count of 31,448 was obtained by querying
`/users/self/alphas?dateCreated>=…&dateCreated<…` one day at a time — the API caps
the `count` field at 10,000, so month buckets under-report and daily buckets do not.

Alpha sources are assigned per scanner batch in `build.py` (`SOURCES`), which is
how the work was actually organised rather than a post-hoc split. The papers
behind the replication batches are deliberately not cited on the page: the writeup
covers the method — restating a paper's conclusion, and the operator vocabulary
that does the restating — not a reading list.

## Caveats

**Everything is in-sample.** All statistics come from the platform's 2019–2023
simulation, and the alphas were selected on that same window. The combined equity
curve is a selection artifact as much as a result; the number worth taking from it
is the drawdown ratio, not the level. Nothing here is a live track record.

**March 2020 is missing.** The platform's PnL recordset carries no entry for that
month for any alpha, so it is absent from every curve. No claim is made about that
period.
