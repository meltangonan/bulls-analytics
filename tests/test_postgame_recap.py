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
from postgame_recap import caption  # noqa: E402
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


def test_east_place_ignores_games_still_in_progress():
    # LeagueGameLog carries a live game with no result (Game 1's as-posted log held GSW at POR at half-time).
    # A blank result must count for no one: here NYK is really 1-0, so the Bulls (1-1) sit second.
    rd.TRI = "CHI"
    rows = [("CHI", "2026-10-05", "W"), ("CHI", "2026-10-07", "L"), ("NYK", "2026-10-05", "W"), ("NYK", "2026-10-07", None)]
    lg = pd.DataFrame(rows, columns=["TEAM_ABBREVIATION", "GAME_DATE", "WL"])
    assert rd.east_place(lg, ["2026-10-07"]) == [[2, False]]


def test_baseline_rebound_rate_is_joined_on_game_and_team():
    import accounting as acc
    # The four-factors and advanced tables do not share a row order; joined, the possession-weighted OREB% is
    # 0.3023 (the row-wise product gave 0.3027). Points per possession is unchanged.
    assert round(acc.P, 4) == 0.3023 and round(acc.V, 4) == 1.1476


def test_notice_marks_fire_once_across_restarts():
    from postgame_recap import due
    final_at = 1000.0
    assert due(0, final_at, final_at + 1, "publishing") == 0  # the process that saw Final
    restarted = final_at + 90  # the restart begins after the mark it reported
    assert due(restarted, final_at, final_at + 19 * 60, "publishing") is None  # 19 min in: nothing yet
    assert due(restarted, final_at, final_at + 20 * 60, "publishing") == 20  # the post should be out by 30
    assert due(restarted, final_at, final_at + 12 * 60, "check") == 10  # sooner when a check is failing
    assert due(final_at + 21 * 60, final_at, final_at + 31 * 60, "check") == 30
    assert due(final_at + 31 * 60, final_at, final_at + 44 * 60, "publishing") is None


def test_as_posted_is_written_once(tmp_path):
    from postgame_recap import SNAPSHOT, snapshot
    data, out = tmp_path / "game", tmp_path / "out"
    data.mkdir(), out.mkdir()
    for name in SNAPSHOT:
        (data / name).write_text("first")
    (out / "recap.json").write_text("{}")
    assert snapshot(data, out).startswith("as-posted/ written")
    assert (data / "as-posted" / "pbp.csv").read_text() == "first" and (data / "as-posted" / "recap.json").exists()
    (data / "pbp.csv").write_text("corrected")  # a rebuild after an NBA.com correction
    assert snapshot(data, out).startswith("as-posted/ kept")
    assert (data / "as-posted" / "pbp.csv").read_text() == "first"


def test_today_prefers_last_night_before_six():
    from datetime import date, datetime
    from postgame_recap import game_day
    assert game_day(datetime(2027, 1, 8, 0, 40)) == [date(2027, 1, 7), date(2027, 1, 8)]
    assert game_day(datetime(2027, 1, 7, 18, 0)) == [date(2027, 1, 7)]


def test_headshot_refresh_downloads_again_and_keeps_the_old_file_on_failure(tmp_path, monkeypatch):
    """NBA.com swaps in new season photos under the same URL, so the recap re-downloads old ones."""
    import requests
    from bulls.data import fetch

    class Reply:
        def __init__(self, body):
            self.content = body

        def raise_for_status(self):
            if self.content is None:
                raise requests.HTTPError("down")

    path = tmp_path / "7.png"
    path.write_bytes(b"last season")
    monkeypatch.setattr(fetch.requests, "get", lambda url, timeout: Reply(b"this season"))
    assert fetch.get_player_headshot(7, cache_dir=str(tmp_path)).read_bytes() == b"last season"
    assert fetch.get_player_headshot(7, cache_dir=str(tmp_path), refresh=True).read_bytes() == b"this season"
    monkeypatch.setattr(fetch.requests, "get", lambda url, timeout: Reply(None))
    assert fetch.get_player_headshot(7, cache_dir=str(tmp_path), refresh=True).read_bytes() == b"this season"


def test_game_one_jerseys_and_leaders_grid():
    d = rd.build("0012600030")
    nums = {r[1]: r[-1] for r in d["box"]["starters"] + d["box"]["bench"]}
    # NBA.com's roster lists Hield as 8 (Wilson's number) and Robinson as 7; the user confirmed Hield wears 7.
    assert (nums["Buddy Hield"], nums["Caleb Wilson"]) == ("7", "8")
    sl = d["season_leaders"]  # preseason leaders show from game 1
    assert (sl["games"], sl["qualify"], len(sl["rows"])) == (1, 1, 14)
    assert sl["rows"][0][1:3] == ["Caleb Wilson", 15.0]
    steals = [r[1] for r in sl["rows"] if r[2 + sl["columns"].index("STL")] == 2.0]
    assert len(steals) == 4  # a four-way tie for the lead, every one shown


def test_an_impossible_nba_biggest_lead_is_skipped_but_nothing_else_is():
    # HOU won 135-117 at DAL (2026-10-09, never trailed); NBA.com listed both biggest leads as 0.
    ours = {"lead_changes": 0, "ties": 0, "chi_lead": 28, "opp_lead": 0, "run_chi": 10, "run_opp": 9}
    nba = {**ours, "chi_lead": 0}
    check, note = rd.compare_flow(ours, nba, 18)
    assert check == "match" and "below the 18-point final margin" in note
    # A possible NBA value that differs still holds the build, and so does any other count.
    assert rd.compare_flow(ours, {**ours, "chi_lead": 25}, 18)[0].startswith("differs")
    assert rd.compare_flow(ours, {**nba, "run_opp": 8}, 18)[0].startswith("differs")
    # Ours must pass the same test: a lead below the margin on both sides is not waved through.
    assert rd.compare_flow({**ours, "chi_lead": 12}, nba, 18)[0].startswith("differs")
    assert rd.compare_flow(ours, ours, 18) == ("match", "")
