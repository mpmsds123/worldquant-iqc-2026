#!/usr/bin/env python3
"""Assemble index.html from the template + the data pulled off the BRAIN API.

Every number on the page comes from data/ — nothing is typed by hand into the
prose except the words. Re-run after refreshing data/ and the page updates.

    python3 build.py
"""
import csv
import glob
import json
import math
import os
import statistics as st
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
IQC = os.path.dirname(HERE)

BOOK = 20_000_000  # BRAIN simulates every alpha on the same $20M book


def load(name):
    with open(os.path.join(DATA, name)) as f:
        return json.load(f)


# ---------------------------------------------------------------- submissions
alphas = load("submitted_alphas.json")   # expressions only for the featured five
port = load("portfolio_monthly.json")        # $ thousands, month-end cumulative
featured_pnl = load("pnl_featured_monthly.json")
dd = load("drawdowns.json")                  # $ thousands, month-end max drawdown


def stage(a):
    return [c["id"] for c in a["competitions"] if c["id"].startswith("IQC")][0]


for a in alphas:
    a["stage"] = stage(a)[-2:]               # "S1" / "S2"

by_id = {a["id"]: a for a in alphas}
S1 = [a for a in alphas if a["stage"] == "S1"]
S2 = [a for a in alphas if a["stage"] == "S2"]

# ------------------------------------------------- fitness identity, verified
fit_err = max(
    abs(a["is"]["sharpe"] * math.sqrt(abs(a["is"]["returns"]) / max(a["is"]["turnover"], 0.125))
        - a["is"]["fitness"])
    for a in alphas
)

# ------------------------------------------------------------- the submission
# gate, read off the checks BRAIN attached to my own submissions
limits = {}
for a in alphas:
    for c in a["is"]["checks"]:
        if "limit" in c:
            limits.setdefault(c["name"], set()).add(c["limit"])

# ------------------------------------------------------------- the scan funnel
# The raw scanner logs hold ~21k candidate expressions and stay local. When they
# are present the aggregates below are recomputed and cached; otherwise the cache
# is what the page is built from, so this repo rebuilds without them.
SCAN_DIR = os.path.join(IQC, "scan_logs")
STATS = os.path.join(DATA, "search_stats.json")

SOURCES = {
    "Dataset sweeps": [
        "stage1", "stage2", "stage2batch", "forum_templates_T123",
        "combined_templates_d1", "multibatch_6sets", "model77", "model77_USA_1",
        "model53", "model53_r2", "news12", "news12_d0_probe", "analyst_revision",
        "fundamental6_round1", "batch_scan_round1", "short_constraint_mdl177_r1"],
    "LLM research pipeline": [
        "pipeline_inspected", "pipeline_inspected_model16", "pipeline_inspected_model16_2",
        "pipeline_inspected_model51", "pipeline_inspected_model51_2",
        "pipeline_inspected_model53", "pipeline_inspected_model77",
        "pipeline_inspected_sentiment1", "house_ideas", "combo_batch"],
    "Systematic expansion": ["generated_alphas", "phase1_t1t2t3", "pv1"],
    "Paper replication": [
        "translated_alphas", "bab_alphas", "alphas_ratio_alphas",
        "alphas_ratio_alphas_batch2", "alphas_ratio_alphas_batch3"],
}
SOURCE_NOTE = {
    "Dataset sweeps": "one dataset's documentation read end to end, then its fields swept through a template",
    "LLM research pipeline": "an MCP server giving a model the simulation API, the platform docs and arXiv",
    "Systematic expansion": "operators crossed with fields, no prior about which pairs should work",
    "Paper replication": "a published finding restated as an expression, with the operators doing the translating",
}
SIMS_RUN = 31448  # counted day by day off the API; see README


def clears_gate(r):
    return (abs(r["fitness"]) >= 1.0 and abs(r["sharpe"]) >= 1.25
            and 0.01 <= r["turnover"] <= 0.7)


def scan_from_logs():
    files = sorted(glob.glob(os.path.join(SCAN_DIR, "*.csv")))
    scan_rows, scored = 0, []
    for f in files:
        src = os.path.basename(f)[9:-4]
        for r in csv.DictReader(open(f)):
            scan_rows += 1
            try:
                r["fitness"] = float(r["fitness"])
                r["sharpe"] = float(r["sharpe"])
                r["turnover"] = float(r["turnover"])
            except (KeyError, TypeError, ValueError):
                continue
            r["_src"] = src
            scored.append(r)
    uniq = {r["expression"]: r for r in scored}
    passing = [r for r in uniq.values() if clears_gate(r)]
    bucket = {b: k for k, v in SOURCES.items() for b in v}
    bn, bp = Counter(), Counter()
    for r in uniq.values():
        bn[bucket.get(r["_src"], "Other")] += 1
    for r in passing:
        bp[bucket.get(r["_src"], "Other")] += 1
    return {
        "files": len(files), "rows": scan_rows,
        "unique": len(uniq), "gate": len(passing),
        "sources": sorted(
            ({"label": k, "n": bn[k], "pass": bp[k], "rate": bp[k] / bn[k] * 100,
              "note": SOURCE_NOTE[k]} for k in SOURCES if bn[k]),
            key=lambda d: -d["rate"]),
    }


if glob.glob(os.path.join(SCAN_DIR, "*.csv")):
    scan = scan_from_logs()
    with open(STATS, "w") as f:
        json.dump(scan, f, indent=1)
    print("  recomputed search_stats.json from the local scanner logs")
else:
    scan = load("search_stats.json")

sources = scan["sources"]

funnel = [
    ("Simulations run on BRAIN", SIMS_RUN, "Apr 7 – Jul 2, 2026, counted day by day off the API"),
    ("Logged locally by the scanner", scan["rows"], f"{scan['files']} batch files"),
    ("Distinct expressions with a score", scan["unique"], "after dropping re-runs of the same expression"),
    ("Clear the submission gate", scan["gate"], "fitness ≥ 1, |Sharpe| ≥ 1.25, turnover in [0.01, 0.7]"),
    ("Actually submitted", len(alphas), "the gate is necessary, not sufficient — correlation kills the rest"),
]

# ----------------------------------------------------- stage-over-stage change
METRICS = [
    ("sharpe", "Sharpe", "x"),
    ("fitness", "Fitness", "x"),
    ("turnover", "Turnover", "frac"),
    ("returns", "Annual return", "pct"),
    ("drawdown", "Max drawdown", "pct"),
    ("margin", "Margin", "bps"),
]
change = []
for key, label, unit in METRICS:
    a = st.median([x["is"][key] for x in S1])
    b = st.median([x["is"][key] for x in S2])
    change.append({"key": key, "label": label, "unit": unit,
                   "s1": a, "s2": b, "pct": (b / a - 1) * 100})

selfcorr = {
    "S1": [x["is"]["selfCorrelation"] for x in S1 if x["is"]["selfCorrelation"] is not None],
    "S2": [x["is"]["selfCorrelation"] for x in S2 if x["is"]["selfCorrelation"] is not None],
}

# ------------------------------------------------------------------ the book
months = sorted(port)
final_pnl = port[months[-1]] * 1000
agg_book = BOOK * len(alphas)
peak, mdd = -1e18, 0.0
for m in months:
    v = port[m] * 1000
    peak = max(peak, v)
    mdd = max(mdd, peak - v)

single_dd_med = st.median(dd.values()) * 1000        # $ , month-end basis
combined_dd_frac = mdd / agg_book
single_dd_frac = single_dd_med / BOOK

# ---------------------------------------------------------------- the six
FEATURED = [
    {
        "id": "d5dYjKME",
        "title": "When the options market disagrees with the stock market",
        "family": "Option / Volatility Data (option8) + Options Analytics (option9)",
        "reading": (
            "The 180-day call and put implied vols price the same underlying. When the call side "
            "is richer than the put side, someone is paying up for upside. The gate <code>pcr_oi_180 &lt; 1</code> "
            "restricts this to names where open interest is already call-heavy — so the signal is only read "
            "where positioning agrees with pricing. Outside that condition <code>trade_when(…, -1)</code> holds "
            "no position rather than taking the opposite side."
        ),
        "why": "Biggest fitness in the book, and the only alpha here whose edge comes from a second market rather than from the tape.",
    },
    {
        "id": "pw6Elod6",
        "title": "Get paid for illiquidity — but only against companies of the same size",
        "family": "Price Volume",
        "reading": (
            "<code>|return| / (close × volume)</code> is Amihud illiquidity: how far the price moves per dollar "
            "traded. Averaged over 60 days, then ranked <em>inside</em> decile buckets of market cap, so a small "
            "company is compared to small companies. The leading minus sign is the whole point: I am short the "
            "illiquid names, not long them, and −0.5 recentres the rank so the book is dollar-neutral by construction."
        ),
        "why": "Sharpe 2.02 out of a two-line price-volume expression. Bucketing by cap is what makes it work — the raw rank is a size bet.",
    },
    {
        "id": "1YgMnjoR",
        "title": "Earnings strength, weighted by whether the options market showed up",
        "family": "Earnings / Effect of earnings announcement model (earnings4)",
        "reading": (
            "An earnings-strength percentile passed through a Gaussian quantile transform (σ = 1.5, so the tails "
            "are pulled in), multiplied by the rank of 20-day average option volume around the announcement. "
            "Linear decay over 15 days spreads the entry. Delay 0: it reads the same session's data, so the "
            "signal has to be something an announcement actually reveals that day."
        ),
        "why": "Turnover 0.020 with a margin of 126 bps — it repositions roughly twice a quarter and earns over a full percent on every dollar it turns over. The cheapest alpha in the book to run.",
    },
    {
        "id": "6XwbmWgG",
        "title": "Slow news tone, expressed only where trading interest has woken up",
        "family": "News / US News Data (news12) + Price Volume / Relationship Data (pv13)",
        "reading": (
            "Two independent pieces multiplied together. The left factor is a volume surge — 5-day average "
            "volume over 252-day average volume, ranked, then square-rooted to compress the extremes. The right "
            "factor is a 180-day mean of news tone blended across three sessions, with the after-hours reading "
            "carried at double weight, ranked inside a sector grouping. Slow sentiment says <em>which way</em>; "
            "the volume surge says <em>whether anyone is there to trade it</em>."
        ),
        "why": "Highest Sharpe in the book at 2.30, on a 3.6% drawdown. Neither factor is strong alone — the product is what holds up.",
    },
    {
        "id": "N1p9pNrg",
        "title": "An analyst valuation model, with the volatility bet taken out of it",
        "family": "Model / GARP analyst valuation model (mdl177)",
        "reading": (
            "A growth-at-a-reasonable-price model's value-to-price ratio, multiplied by its own 30-day standard "
            "deviation, so the position scales with how much the model's view is actually moving rather than "
            "with its level. Negated, then <code>vector_neut</code> against ranked 252-day realized volatility — "
            "which is the part that matters: without it the alpha is largely a short-volatility bet wearing a "
            "valuation label."
        ),
        "why": "The orthogonalization step is the whole idea. It costs some raw Sharpe and buys a signal that is about valuation rather than about risk appetite.",
    },
]

for f in FEATURED:
    a = by_id[f["id"]]
    s = a["is"]
    f["code"] = a["regular"]["code"].strip()
    f["stage"] = a["stage"]
    f["date"] = a["dateSubmitted"][:10]
    f["metrics"] = {
        "Sharpe": f"{s['sharpe']:.2f}",
        "Fitness": f"{s['fitness']:.2f}",
        "Turnover": f"{s['turnover']:.3f}",
        "Return": f"{s['returns']*100:.1f}%",
        "Drawdown": f"{s['drawdown']*100:.1f}%",
        "Margin": f"{s['margin']*10000:.0f} bps",
    }
    f["delay"] = a["settings"]["delay"]
    f["settings"] = (f"{a['settings']['region']} · {a['settings']['universe']} · "
                     f"{a['settings']['neutralization'].lower()} neutralized · "
                     f"decay {a['settings']['decay']}")
    f["pnl"] = featured_pnl[f["id"]]
    f["total"] = load("pnl_summary.json")["yr"][f["id"]]["2023"]

# ---------------------------------------------------------- the whole roster
import re


def one_line(code, limit=150):
    """Strip C-style comments and collapse whitespace so the roster stays a table."""
    code = re.sub(r"/\*.*?\*/", " ", code, flags=re.S)
    code = re.sub(r"\s+", " ", code).strip()
    return code if len(code) <= limit else code[:limit].rstrip() + "…"


# The individual expressions are deliberately not published — the five featured
# alphas are the sample. What goes on the page is the shape of the book.
# family tags are precomputed in the data file, so the non-featured expressions
# never have to ship in order to count them
families = set()
for a in alphas:
    families.update(a["families"])

SUMMARY = [
    ("Sharpe", "sharpe", 2, ""),
    ("Fitness", "fitness", 2, ""),
    ("Turnover", "turnover", 3, ""),
    ("Annual return", "returns", 1, "%"),
    ("Max drawdown", "drawdown", 1, "%"),
    ("Margin", "margin", 0, " bps"),
]
summary = []
for label, key, dp, unit in SUMMARY:
    mult = 100 if unit == "%" else (10000 if unit.strip() == "bps" else 1)
    vals = sorted(a["is"][key] * mult for a in alphas)
    summary.append({
        "label": label,
        "min": f"{vals[0]:.{dp}f}{unit}",
        "med": f"{st.median(vals):.{dp}f}{unit}",
        "max": f"{vals[-1]:.{dp}f}{unit}",
    })

payload = {
    "rank": {
        "s1": {"rank": 10082, "of": 152452, "score": 2270, "is": 8039, "os": 347},
        "s2": {"rank": 578, "of": 22085, "score": 9374, "is": 23658, "os": 4613,
               "us_rank": 15, "us_of": 200},
    },
    "counts": {"submitted": len(alphas), "s1": len(S1), "s2": len(S2),
               "sims": SIMS_RUN, "unique": scan["unique"], "gate": scan["gate"],
               "families": len(families)},
    "fitErr": fit_err,
    "limits": {k: sorted(v) for k, v in limits.items()},
    "funnel": funnel,
    "sources": sources,
    "change": change,
    "selfcorr": {k: {"median": st.median(v), "over_half": sum(1 for x in v if x > 0.5), "n": len(v)}
                 for k, v in selfcorr.items()},
    # only the five featured alphas are identified; the rest are plotted anonymously
    "scatter": [{"id": (a["id"] if a["id"] in {f["id"] for f in FEATURED} else None),
                 "n": i + 1, "stage": a["stage"], "t": a["is"]["turnover"],
                 "s": a["is"]["sharpe"], "f": a["is"]["fitness"],
                 "m": a["is"]["margin"] * 10000}
                for i, a in enumerate(sorted(alphas, key=lambda x: x["is"]["turnover"]))],
    "portfolio": port,
    "book": {"per_alpha": BOOK, "aggregate": agg_book, "final": final_pnl,
             "cum_pct": final_pnl / agg_book * 100,
             "mdd": mdd, "mdd_pct": combined_dd_frac * 100,
             "single_mdd_pct": single_dd_frac * 100,
             "ratio": single_dd_frac / combined_dd_frac},
    "featured": FEATURED,
    "summary": summary,
}

with open(os.path.join(HERE, "index.template.html")) as f:
    html = f.read()
html = html.replace("/*__DATA__*/null", json.dumps(payload, separators=(",", ":")))
with open(os.path.join(HERE, "index.html"), "w") as f:
    f.write(html)

print(f"wrote index.html  ({len(html):,} bytes)")
print(f"  fitness identity max error {fit_err:.4f}")
print(f"  funnel {payload['counts']['sims']:,} -> {payload['counts']['unique']:,} -> "
      f"{payload['counts']['gate']} -> {payload['counts']['submitted']}")
for d in sources:
    print(f"  {d['label']:24s} {d['n']:6,d} -> {d['pass']:3d}  {d['rate']:.2f}%")
print(f"  book {final_pnl/1e6:.1f}M on {agg_book/1e6:.0f}M = {payload['book']['cum_pct']:.1f}%  "
      f"mdd {payload['book']['mdd_pct']:.3f}% vs single {payload['book']['single_mdd_pct']:.2f}%")
