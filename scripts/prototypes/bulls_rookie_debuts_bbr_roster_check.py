"""Compare Basketball-Reference's Bulls rookies (Exp = R) with our rookie-debut cohort, 1976-77 to 2025-26.

An independent check of the cohort in ``bulls_rookie_debuts.py``: Basketball-Reference marks a
rookie "R" on each Bulls season roster (https://www.basketball-reference.com/teams/CHI/<year>.html,
saved under cache/basketball_reference/, fetched one page per 6 seconds on 2026-10-13). Every BBR
rookie should be an eligible debut here, and every eligible debut a BBR rookie.

Usage: bulls_rookie_debuts_bbr_roster_check.py <bbr cache dir> <first_bulls_games_audit.csv> <out.csv>
"""
import re, sys, unicodedata
from pathlib import Path
import pandas as pd
cache, audit_path, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])

# Same player, different spelling on the two sites (checked by debut season and team).
ALIASES = {"David Greenwood": "Dave Greenwood", "Charles R. Jones": "Charles Jones",
           "Norman Richardson": "Norm Richardson", "Omer Asik": "Ömer Aşık"}


def norm(name):
    name = ALIASES.get(str(name), str(name))
    s = unicodedata.normalize("NFKD", name).replace("ı", "i")
    s = s.encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\b\.?", "", s)
    return re.sub(r"[^a-z]", "", s)

rows = []
for year in range(1977, 2027):
    text = (cache / f"CHI-{year}.html").read_text(errors="ignore")
    roster = text[text.index('id="roster"'):]
    roster = roster[:roster.index("</table>")]
    for tr in re.findall(r"<tr >(.*?)</tr>", roster, re.S):
        m = re.search(r'data-append-csv="([^"]+)"[^>]*><a href="[^"]+">([^<]+)</a>', tr)
        e = re.search(r'data-stat="years_experience"[^>]*>([^<]*)<', tr)
        if m and e:
            rows.append({"season_end_year": year, "bbr_id": m.group(1),
                         "player": unicodedata.normalize("NFC", m.group(2)), "exp": e.group(1)})
bbr = pd.DataFrame(rows)
bbr["key"] = bbr["player"].map(norm)
rookies = bbr[bbr["exp"].eq("R")]

audit = pd.read_csv(audit_path)
audit["key"] = audit["player"].map(norm)
ours = audit[audit["eligible"]]

merged = rookies.merge(audit[["key", "player", "season_end_year", "points", "eligible", "rookie_debut",
                              "aba_veteran", "entry_rule"]],
                       left_on=["key", "season_end_year"], right_on=["key", "season_end_year"],
                       how="left", suffixes=("_bbr", ""))
merged["season_end_year_bbr"] = merged["season_end_year"]
merged["agree"] = merged["eligible"].eq(True)
only_ours = ours[~(ours["key"] + ours["season_end_year"].astype(str)).isin(rookies["key"] + rookies["season_end_year"].astype(str))]
print(f"BBR rookies on Bulls rosters: {len(rookies)}; our eligible: {len(ours)}; agree: {int(merged['agree'].sum())}")
print("\nBBR rookie, not in our cohort:")
print(merged[~merged["agree"]][["season_end_year_bbr", "player_bbr", "bbr_id", "season_end_year",
                                "points", "eligible", "aba_veteran", "entry_rule"]].to_string(index=False))
print("\nOur cohort, not a BBR Bulls rookie:")
print(only_ours[["season_end_year", "player", "points", "entry_rule"]].to_string(index=False))
merged.to_csv(out, index=False)
