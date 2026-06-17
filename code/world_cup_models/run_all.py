"""End-to-end: fit both models, Monte-Carlo the tournament, join the live market
snapshot, and write results.json + charts for the blog post and the website.

    python run_all.py [--sims 30000]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import models as M
import tournament as T

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
CHARTS = HERE.parents[1] / "static" / "charts" / "world-cup-models"


def fit_models():
    df = M.load_results(since="2014-01-01")
    counts = pd.concat([df.home_team, df.away_team]).value_counts()
    G = json.load(open(DATA / "groups_2026.json"))["groups"]
    groups = {L: [M.canon(t) for t in teams] for L, teams in G.items()}
    universe = sorted(set(counts[counts >= 20].index) | {t for g in groups.values() for t in g})
    print(f"fitting Dixon-Coles on {len(df)} matches, {len(universe)} teams ...")
    dc = M.fit_dixon_coles(df, universe)
    print(f"  home_adv={dc.home_adv:.3f}  rho={dc.rho:.3f}")
    print("fitting Elo ...")
    elo = M.fit_elo(df)
    return df, groups, dc, elo


def devig(d: dict[str, float]) -> dict[str, float]:
    s = sum(d.values())
    return {k: v / s for k, v in d.items()} if s else d


def tonight_matches(df, dc, elo, snap):
    """Compare DC / Elo / Polymarket for each scheduled match in the snapshot."""
    fx = df  # not used; fixtures come from results.csv directly
    res = pd.read_csv(DATA / "results.csv")
    res = res[(res.tournament == "FIFA World Cup") & (res.date >= "2026-06-01")]
    fixtures = {}
    for _, r in res.iterrows():
        fixtures[(M.canon(r.home_team), M.canon(r.away_team))] = r.date

    out = []
    for m in snap["pm_matches"]:
        # parse home/away from the event title "Home vs. Away"
        title = m["title"].replace(" vs. ", " vs ")
        home, away = [s.strip() for s in title.split(" vs ", 1)]
        home_c, away_c = M.canon(home), M.canon(away)
        # Polymarket legs -> home/draw/away
        pm = {"home": None, "draw": None, "away": None}
        for o in m["outcomes"]:
            lab = M.canon(o["label"])
            if lab == home_c:
                pm["home"] = o["prob"]
            elif lab == away_c:
                pm["away"] = o["prob"]
            else:
                pm["draw"] = o["prob"]
        if None in pm.values():
            continue
        pm_dv = devig(pm)
        dcp = dc.match_probs(home_c, away_c, neutral=True)
        elop = elo.match_probs(home_c, away_c, neutral=True)
        out.append({
            "home": home, "away": away, "slug": m["slug"],
            "dc": dcp, "elo": elop,
            "pm_raw": pm, "pm": pm_dv,
            "pm_overround": round(sum(pm.values()), 4),
            # model edge on each outcome vs de-vigged market (DC)
            "edge_dc": {k: dcp[k] - pm_dv[k] for k in ("home", "draw", "away")},
        })
    return out


def champion_table(dc_champ, elo_champ, snap, groups):
    in_tournament = {M.canon(t) for g in groups.values() for t in g}
    pm = {M.canon(x["team"]): x["yes_price"] for x in snap["pm_champion"]
          if M.canon(x["team"]) in in_tournament}
    hl = {M.canon(x["team"]): x["mid"] for x in snap["hl_champion"]
          if M.canon(x["team"]) in in_tournament}
    pm_dv = devig(pm)
    hl_dv = devig(hl)
    rows = []
    for t in sorted(in_tournament):
        rows.append({
            "team": t,
            "dc": dc_champ.get(t, 0.0),
            "elo": elo_champ.get(t, 0.0),
            "pm_raw": pm.get(t), "pm": pm_dv.get(t),
            "hl_raw": hl.get(t), "hl": hl_dv.get(t),
        })
    rows.sort(key=lambda r: -(r["pm"] or 0))
    return rows, {
        "pm_overround": round(sum(pm.values()), 4),
        "hl_overround": round(sum(hl.values()), 4),
        "n_pm": len(pm), "n_hl": len(hl),
    }


def make_charts(champ_rows, tonight, meta):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    CHARTS.mkdir(parents=True, exist_ok=True)
    BL, OR, GR = "#1f77b4", "#e76f51", "#2a9d8f"

    # 1) champion: model (DC) vs PM vs HL, top 16 by PM
    top = [r for r in champ_rows if r["pm"]][:16]
    names = [r["team"] for r in top]
    y = np.arange(len(names))[::-1]
    fig, ax = plt.subplots(figsize=(9, 7.5))
    h = 0.26
    ax.barh(y + h, [r["dc"] * 100 for r in top], h, label="Dixon-Coles (model)", color=BL)
    ax.barh(y, [r["pm"] * 100 for r in top], h, label="Polymarket (de-vig)", color=OR)
    ax.barh(y - h, [(r["hl"] or 0) * 100 for r in top], h, label="Hyperliquid (de-vig)", color=GR)
    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=9)
    ax.set_xlabel("implied probability of winning the World Cup (%)")
    ax.set_title("Who wins the 2026 World Cup? Model vs two markets")
    ax.legend(loc="lower right"); ax.grid(axis="x", alpha=0.2)
    fig.tight_layout(); fig.savefig(CHARTS / "champion_three_way.png", dpi=140); plt.close(fig)

    # 2) PM vs HL scatter (cross-venue pricing)
    pts = [(r["pm"] * 100, (r["hl"] or 0) * 100, r["team"]) for r in champ_rows if r["pm"] and r["hl"]]
    fig, ax = plt.subplots(figsize=(7.2, 7))
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    ax.scatter(xs, ys, s=26, color=BL, alpha=0.8)
    lim = max(max(xs), max(ys)) * 1.08
    ax.plot([0, lim], [0, lim], color="#888", lw=1, ls="--")
    for x, yy, t in pts:
        if x > 4 or yy > 4 or abs(x - yy) > 1.2:
            ax.annotate(t, (x, yy), fontsize=7.5, xytext=(3, 3), textcoords="offset points")
    ax.set_xlabel("Polymarket de-vigged prob (%)"); ax.set_ylabel("Hyperliquid de-vigged prob (%)")
    ax.set_title("Same bet, two venues: Polymarket vs Hyperliquid HIP-4")
    ax.set_xlim(0, lim); ax.set_ylim(0, lim); ax.grid(alpha=0.2)
    fig.tight_layout(); fig.savefig(CHARTS / "pm_vs_hl_scatter.png", dpi=140); plt.close(fig)

    # 3) tonight: model vs market, home-win prob per match
    labels = [f"{m['home'][:3].upper()}-{m['away'][:3].upper()}" for m in tonight]
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(9.5, 5))
    w = 0.26
    ax.bar(x - w, [m["dc"]["home"] * 100 for m in tonight], w, label="Dixon-Coles", color=BL)
    ax.bar(x, [m["elo"]["home"] * 100 for m in tonight], w, label="Elo", color=GR)
    ax.bar(x + w, [m["pm"]["home"] * 100 for m in tonight], w, label="Polymarket (de-vig)", color=OR)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("P(home team wins) %")
    ax.set_title("Upcoming matches: home-win probability, model vs market")
    ax.legend(); ax.grid(axis="y", alpha=0.2)
    fig.tight_layout(); fig.savefig(CHARTS / "tonight_home_win.png", dpi=140); plt.close(fig)
    print(f"charts -> {CHARTS}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sims", type=int, default=30000)
    args = ap.parse_args()

    df, groups, dc, elo = fit_models()
    snap = json.load(open(DATA / "market_snapshot_latest.json"))

    print(f"Monte-Carlo: {args.sims} sims x 2 models ...")
    dc_champ, dc_final = T.run_dc(dc, groups, n=args.sims)
    elo_champ, elo_final = T.run_elo(elo, groups, n=args.sims)

    tonight = tonight_matches(df, dc, elo, snap)
    champ_rows, champ_meta = champion_table(dc_champ, elo_champ, snap, groups)

    # Elo ratings for the post
    elo_top = sorted(elo.rating.items(), key=lambda x: -x[1])
    elo_top = [{"team": t, "rating": round(r, 1)} for t, r in elo_top
               if t in {M.canon(x) for g in groups.values() for x in g}][:12]

    results = {
        "as_of_market": snap["fetched_at_utc"],
        "sims": args.sims,
        "model_params": {"dc_home_adv": dc.home_adv, "dc_rho": dc.rho,
                         "elo_home_adv": elo.home_adv, "elo_top": elo_top},
        "champion": champ_rows,
        "champion_meta": champ_meta,
        "champion_finalist": {"dc": dc_final, "elo": elo_final},
        "tonight": tonight,
    }
    (DATA / "results.json").write_text(json.dumps(results, indent=2))
    print(f"results -> {DATA / 'results.json'}")

    make_charts(champ_rows, tonight, champ_meta)

    # console summary
    print("\n=== CHAMPION (top 12 by Polymarket) ===")
    print(f"{'team':16s} {'DC':>6} {'Elo':>6} {'PM':>6} {'HL':>6}")
    for r in champ_rows[:12]:
        print(f"{r['team']:16s} {r['dc']*100:5.1f}% {r['elo']*100:5.1f}% "
              f"{(r['pm'] or 0)*100:5.1f}% {(r['hl'] or 0)*100:5.1f}%")
    print(f"\nPM overround {champ_meta['pm_overround']}, HL overround {champ_meta['hl_overround']}")
    print("\n=== TONIGHT (home-win %) ===")
    for m in tonight:
        print(f"{m['home']:14s} v {m['away']:16s} "
              f"DC {m['dc']['home']*100:4.0f} Elo {m['elo']['home']*100:4.0f} PM {m['pm']['home']*100:4.0f}")


if __name__ == "__main__":
    main()
