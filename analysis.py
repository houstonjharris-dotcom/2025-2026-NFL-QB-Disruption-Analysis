"""
2025 NFL QB Performance Under Disruption

I built this as a follow-up to my first QB efficiency project.
Instead of trying to rank total quarterback ability, I wanted to ask a
smaller question: what happened to high-volume QBs when a dropback was
disrupted by a QB hit or sack?

Data: nflverse 2025 regular-season play-by-play.
Sample: 20 quarterbacks with the most dropbacks.
"""

import pandas as pd

DATA_FILE = "data/play_by_play_2025.csv.gz"

df = pd.read_csv(DATA_FILE, compression="gzip", low_memory=False)

# Keep regular-season QB dropbacks with an identified passer.
pbp = df[
    (df["season_type"] == "REG")
    & (df["qb_dropback"] == 1)
    & df["passer_player_id"].notna()
].copy()

# This is intentionally called "disruption," not "pressure."
# nflverse gives us QB-hit and sack indicators, but this is not a full
# tracking-data pressure measure.
pbp["disrupted"] = (pbp["qb_hit"] == 1) | (pbp["sack"] == 1)
pbp["turnover"] = (pbp["interception"] == 1) | (pbp["fumble_lost"] == 1)
pbp["positive_epa"] = pbp["qb_epa"] > 0

# Use the 20 highest-volume QBs by dropbacks.
volume = (
    pbp.groupby(["passer_player_id", "passer_player_name"])
    .size()
    .sort_values(ascending=False)
    .head(20)
)

top_ids = set(volume.index.get_level_values(0))
sample = pbp[pbp["passer_player_id"].isin(top_ids)].copy()

rows = []

for (player_id, player), plays in sample.groupby(
    ["passer_player_id", "passer_player_name"]
):
    disrupted = plays[plays["disrupted"]]
    clean = plays[~plays["disrupted"]]

    rows.append(
        {
            "player": player,
            "team": plays["posteam"].mode().iat[0],
            "dropbacks": len(plays),
            "disrupted_dropbacks": len(disrupted),
            "disruption_rate": 100 * len(disrupted) / len(plays),
            "clean_epa_per_dropback": clean["qb_epa"].mean(),
            "disrupted_epa_per_dropback": disrupted["qb_epa"].mean(),
            "positive_epa_rate_when_disrupted":
                100 * disrupted["positive_epa"].mean(),
            "sack_rate_when_disrupted": 100 * disrupted["sack"].mean(),
            "turnover_rate_when_disrupted":
                100 * disrupted["turnover"].mean(),
        }
    )

qbs = pd.DataFrame(rows)

# I do not grade disruption rate because protection and scheme have a big
# effect on how often a quarterback gets hit. The grade focuses on the
# outcome of the disrupted dropbacks.
weights = {
    "disrupted_epa_per_dropback": 0.50,
    "positive_epa_rate_when_disrupted": 0.20,
    "sack_rate_when_disrupted": 0.20,
    "turnover_rate_when_disrupted": 0.10,
}

positive = [
    "disrupted_epa_per_dropback",
    "positive_epa_rate_when_disrupted",
]
negative = [
    "sack_rate_when_disrupted",
    "turnover_rate_when_disrupted",
]

for metric in positive:
    qbs[metric + "_pct"] = qbs[metric].rank(pct=True) * 100

for metric in negative:
    qbs[metric + "_pct"] = (1 - qbs[metric].rank(pct=True)) * 100

qbs["model_score"] = sum(
    qbs[metric + "_pct"] * weight for metric, weight in weights.items()
)

# Put the model on an easier-to-read football-style scale.
mean = qbs["model_score"].mean()
std = qbs["model_score"].std(ddof=0)

qbs["disruption_performance_grade"] = (
    75 + 9 * ((qbs["model_score"] - mean) / std)
).clip(60, 96)

qbs = qbs.sort_values("disruption_performance_grade", ascending=False)

print(
    qbs[
        ["player", "team", "disruption_performance_grade"]
    ].to_string(index=False)
)
