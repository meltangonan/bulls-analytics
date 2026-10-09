"""Postgame recap: the checks that keep a wrong number off the slides, run on saved NBA.com feeds.

Game 1 (0012600030) posted a fake 18-0 run because a period-start row carried a later score; the checks
below make the build wait for NBA.com instead of drawing from a lagging or mis-scored feed. The pinned
Game 1 values were verified against NBA.com after its overnight correction (independent review, Oct 8).
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

PIPELINE = Path(__file__).resolve().parents[1] / "postgame-recaps/pipeline"
sys.path.insert(0, str(PIPELINE))
import recap_data as rd  # noqa: E402
from deliver import clean_png  # noqa: E402
from game_night import caption  # noqa: E402
from paths import game_dir  # noqa: E402


def pbp(game_id):
    return rd.read(game_dir(game_id), "pbp.csv")


@pytest.mark.parametrize("game_id", ["0012600030", "0022500248", "0022500943", "0022500240"])
def test_clean_games_build_and_match_nba_counts(game_id):
    # Preseason, regulation, overtime and double overtime.
    d = rd.build(game_id)
    assert d["flow"]["nba_check"] == "match"
    assert sum(d["quarters"]["chi"]) <= d["chi"]["score"]  # overtime points sit outside the four quarters
    assert d["flow"]["periods"] == {"0022500943": 5, "0022500240": 6}.get(game_id, 4)


def test_game_one_matches_nba_after_correction():
    d = rd.build("0012600030")
    assert (d["chi"]["score"], d["opp"]["score"]) == (124, 117)
    assert d["quarters"]["chi"] == [29, 33, 31, 31] and d["quarters"]["opp"] == [40, 24, 26, 27]
    f = d["flow"]
    assert (f["chi_lead"], f["opp_lead"], f["lead_changes"], f["ties"]) == (10, 15, 4, 3)
    assert (f["run_chi"], f["run_opp"]) == (11, 14)  # the posted slide said 18-0
    assert d["awards"][0][2:] == ["Leonard Miller", "14 PTS on 5-7 FG, 2 STL"]
    assert caption(d) == ("The Chicago Bulls beat the Phoenix Suns 124-117 at the United Center.\n\n"
                          "Stats via NBA.com as of game night. The NBA can revise official stats after a game.\n\n"
                          "#chicagobulls #bullsnation #nbadata #nbastats #basketballanalytics\n")


def test_score_steps_flag_only_the_scrambled_feed():
    assert rd.score_steps(pbp("0012600030")) == []
    assert rd.score_steps(pbp("0012600027"))  # DEN at UTA, still scrambled on NBA.com


def test_play_by_play_behind_the_box_score_waits(monkeypatch):
    real = rd.read

    def lagging(folder, name, **kw):
        frame = real(folder, name, **kw)
        if name == "pbp.csv":  # the last made free throw has not reached the play-by-play yet
            frame = frame.drop(frame.index[frame.actionType == "Free Throw"][-1])
        return frame

    monkeypatch.setattr(rd, "read", lagging)
    with pytest.raises(rd.NotReady):
        rd.build("0012600030")


def test_box_tables_must_agree():
    g = game_dir("0012600030")
    players, teams, ff = rd.read(g, "players.csv"), rd.read(g, "teams.csv"), rd.read(g, "ff_team.csv")
    assert rd.feeds_agree(players, teams, ff) == []
    stale = teams.copy()
    stale.loc[stale.teamTricode == "CHI", ["fieldGoalsAttempted", "reboundsTotal"]] -= 1  # before the correction
    found = rd.feeds_agree(players, stale, ff)
    assert "CHI player rows do not add up to the team totals" in found
    assert "CHI four factors do not match the box score" in found


def test_game_logs_must_show_tonight_like_the_box_score():
    g = game_dir("0012600030")
    players, teams = rd.read(g, "players.csv"), rd.read(g, "teams.csv")
    pg, lg = rd.read(g, "player_games.csv"), rd.read(g, "league_games.csv")
    assert rd.logs_match("0012600030", players, teams, pg, lg) == []
    lagging = lg.copy()
    lagging.loc[lagging.TEAM_ID == rd.BULLS, "REB"] -= 1
    assert rd.logs_match("0012600030", players, teams, pg, lagging) == ["league game log (LeagueGameLog, teams)"]


def test_decider_names_the_scoring_play_not_a_missed_and_one():
    p = pbp("0012600030")
    i = p.index[(p.actionType == "Made Shot") & p.description.str.startswith("Peterson 26'")][0]
    miss = p.loc[i].copy()
    miss["actionType"], miss["description"], miss["shotValue"] = "Free Throw", "MISS Peterson Free Throw 1 of 1", 0
    miss["scoreHome"] = miss["scoreAway"] = float("nan")
    p = pd.concat([p.loc[:i], miss.to_frame().T, p.loc[i + 1:]]).reset_index(drop=True)
    for c in ("period", "shotValue"):
        p[c] = pd.to_numeric(p[c])
    rd.TRI = "CHI"
    decider = [n for n in rd.flow(p, True, "PHX")["notes"] if n["kind"] == "decider"]
    assert [n["label"] for n in decider] == ["Peterson 3"]


def test_slides_keep_image_data_only(tmp_path):
    # Instagram must never label a post as AI-made: a PNG may carry nothing but the picture.
    png = (b"\x89PNG\r\n\x1a\n" + bytes.fromhex("0000000d49484452000000010000000108060000001f15c489")
           + bytes.fromhex("0000000a49444154789c63000100000500010d0a2db4") + bytes.fromhex("0000000049454e44ae426082"))
    import struct, zlib
    text = b"Software\x00made with AI"
    chunk = struct.pack(">I", len(text)) + b"tEXt" + text + struct.pack(">I", zlib.crc32(b"tEXt" + text))
    path = tmp_path / "slide.png"
    path.write_bytes(png[:33] + chunk + png[33:])
    assert clean_png(path) == ["tEXt"]
    assert path.read_bytes() == png and clean_png(path) == []
