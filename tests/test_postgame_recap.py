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
from watch_build import Watcher  # noqa: E402


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
    from deliver import SNAPSHOT, snapshot
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


def test_a_sixth_marked_starter_moves_to_the_bench(monkeypatch):
    # NBA.com's preseason box gives MEM six positions; Quinten Post (C, 17:09) entered at 5:52 of the 1st.
    # ESPN's starters for this game are the five below.
    monkeypatch.setattr(rd, "BULLS", 1610612763)
    g = game_dir("0012600037")
    players = rd.read(g, "players.csv")
    assert players.position[players.teamId == rd.BULLS].notna().sum() == 6
    ids = rd.starters(players, pbp("0012600037"))
    b = rd.box(players, rd.read(g, "roster.csv", dtype={"NUM": str}), ids)
    assert {r[1] for r in b["starters"]} == {"Cedric Coward", "Cameron Boozer", "Jaylen Wells", "Zach Edey", "Ty Jerome"}
    assert "Quinten Post" in [r[1] for r in b["bench"]]
    assert b["minutes"] == [69, 171, 240]


def test_an_unsettled_starting_five_stops_the_build(monkeypatch):
    monkeypatch.setattr(rd, "BULLS", 1610612763)
    frame = pbp("0012600037")
    frame = frame[frame.description != "SUB: Post FOR Boozer"]  # Post now looks on the floor at the tip
    with pytest.raises(ValueError, match="starting five"):
        rd.starters(rd.read(game_dir("0012600037"), "players.csv"), frame)


def test_every_saved_game_settles_five_starters_per_team():
    folders = [p.parent for p in game_dir("0012600037").parent.glob("*/players.csv")]
    folders += [p.parent for p in game_dir("0022500248").parent.glob("*/players.csv")]
    assert len(folders) >= 19
    for g in folders:
        players, frame = rd.read(g, "players.csv"), rd.read(g, "pbp.csv")
        for team_id in players.teamId.unique():
            assert len(rd.starters(players, frame, team_id)) == 5, g.name


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


def test_watcher_prints_changes_and_a_heartbeat_not_every_poll():
    # Lines from the Oct 9 build log; the clock is pinned so "min after Final" reads from the log's stamps.
    from datetime import datetime
    now = datetime(2026, 10, 9, 22, 30).timestamp()
    log = ["21:52:32 game 0012600037; restarted, Final first seen 21:43",
           "21:52:32 final: 104-100 (away-home)",
           "missing or empty: ff_team.csv: not published (no rows)",
           "not published yet: Bulls shots, four factors, misc (head-to-head)",
           "21:53:11 not ready, pulling again in 90 s",
           "missing or empty: ff_team.csv: not published (no rows)",
           "not published yet: Bulls shots, four factors, misc (head-to-head)",
           "21:55:09 not ready, pulling again in 90 s",
           "not published yet: four factors, misc (head-to-head)",
           "21:57:06 not ready, pulling again in 90 s",
           "CANVA COPY",
           "21:59:09 done: CHI 100, MEM 104; 8 slides; game flow vs NBA.com: match"]
    w = Watcher()
    out = [u for line in log for u in w.feed(line + "\n", now)]
    assert out == ["game 0012600037; restarted, Final first seen 21:43",
                   "final: 104-100 (away-home)",
                   "10 min after Final; waiting on: not published yet: Bulls shots, four factors, misc (head-to-head)",
                   "14 min after Final; waiting on: not published yet: four factors, misc (head-to-head)",
                   "done: CHI 100, MEM 104; 8 slides; game flow vs NBA.com: match"]
    assert not w.ended and w.tick(now + 60) == []
    assert w.tick(now + 180) == ["50 min after Final; still waiting on: not published yet: four factors, misc (head-to-head)"]
    assert w.feed("21:59:09 restart: python postgame_recap.py 0012600037 1791600198\n", now) == [] and w.ended


def test_watcher_warns_once_when_the_build_goes_silent():
    from datetime import datetime
    now = datetime(2026, 10, 9, 22, 0).timestamp()
    w = Watcher()
    w.feed("21:59:30 not final yet (Q4 2:10)\n", now)
    assert w.tick(now + 9 * 60) == []
    assert w.tick(now + 10 * 60) == ["the build has logged nothing for 10 min; it may be stuck"]
    assert w.tick(now + 11 * 60) == []  # once per silence, not every second
    w.feed("22:11:00 not final yet (Q4 0:40)\n", now + 11 * 60)
    assert w.tick(now + 21 * 60) == ["the build has logged nothing for 10 min; it may be stuck"]


def test_the_build_stops_for_review_before_anything_reaches_the_phone():
    w = Watcher()
    line = "22:30:00 review: slides await Claude's review; deliver with python deliver.py 0012600037\n"
    assert w.feed(line, 0) == ["slides exported and measured; Claude's review is next (nothing is on the phone yet)"]
    assert w.ended
    source = (Path(__file__).resolve().parents[1] / "postgame-recaps/pipeline/postgame_recap.py").read_text()
    assert "deliver(" not in source and "--icloud" not in source


def test_layout_flags_collisions_and_holes_not_the_normal_page():
    from export_slides import layout, verdict
    t = lambda text, x0, y0, x1, y1: {"t": text, "x0": x0, "y0": y0, "x1": x1, "y1": y1}
    page = {"texts": [t("Title", 25, 60, 600, 110), t("Josh", 40, 300, 100, 320), t("Giddey", 40, 326, 120, 346),
                      t("Data via NBA.com", 25, 1408, 600, 1428)],
            "shapes": [t("", 25, 360, 1055, 1300)]}
    l = layout(page)
    assert l["overlaps"] == [] and l["off_margin"] == [] and l["hole"] == 190 and l["above_footer"] == 108
    assert verdict("02-final-score", l).startswith("layout: 02-final-score: ok")
    page["texts"][2] = t("Giddey", 40, 315, 1070, 335)  # runs into the line above and past the right margin
    assert verdict("02-final-score", layout(page)).startswith('layout: 02-final-score: FIX: overlap "Josh" / "Giddey"; off the margin "Giddey"')
    page["texts"][2] = t("Giddey", 40, 326, 120, 346)
    page["shapes"][0] = t("", 25, 600, 1055, 1405)  # a hole above the chart, which now crowds the footer
    assert verdict("x", layout(page)) == "layout: x: LOOK: empty band 254 px from y=346; only 3 px above the footer"


def test_early_look_names_overtime_and_checks_the_sums():
    from early_look import look
    lines = look("0022500240")
    assert lines[0] == "L CHI 147, UTA 150 (2OT)"
    assert lines[1] == "box score: player rows add up to the team totals, four factors match"
    assert lines[2].startswith("CHI leaders: White 27 pts")


def test_delivery_replaces_an_earlier_copy_in_icloud_drive(tmp_path, monkeypatch):
    import deliver
    out = tmp_path / "output" / "0022500943"
    (out / "slides").mkdir(parents=True)
    (out / "recap.json").write_text('{"date_short": "Mar 10", "home": false, "chi": {"tri": "CHI"}, "opp": {"tri": "GSW"}}')
    monkeypatch.setattr(deliver, "OUTPUT", tmp_path / "output")
    monkeypatch.setattr(deliver, "ICLOUD", tmp_path / "icloud")
    folder = tmp_path / "icloud" / "Mar 10 CHI at GSW"
    folder.mkdir(parents=True)
    (folder / "09-old-page.png").write_bytes(b"rejected build")
    slide = out / "slides" / "02-final-score.png"
    slide.write_bytes(b"reviewed")
    assert deliver.to_icloud("0022500943", [slide]) == f"copied to {folder}"
    assert [p.name for p in folder.iterdir()] == ["02-final-score.png"]


def test_watcher_says_a_failing_check_once_not_every_poll():
    w = Watcher()
    w.feed("22:04:26 final: 125-124 (away-home)\n", 0)
    poll = ["pulled 0012600002", "0012600002: not ready: play-by-play score steps are off at 3 rows",
            "22:07:13 not ready, pulling again in 90 s"]
    first = [u for line in poll for u in w.feed(line + "\n", 0)]
    again = [u for line in poll for u in w.feed(line + "\n", 0)]
    assert first[:2] == ["every slide feed is published; running the checks",
                         "0012600002: not ready: play-by-play score steps are off at 3 rows"]
    assert again == []


def test_a_misprinted_running_score_is_recomputed_but_a_scrambled_feed_still_waits(monkeypatch):
    # MIN at MIA, 2026-10-10: a re-entered and-one printed 84-87 on the shot and 82-87 on its free throw.
    pbp = rd.read(game_dir("0012600002"), "pbp.csv")
    assert len(rd.score_steps(pbp)) == 3
    fixed, changed = rd.repair_scores(pbp)
    assert changed == 2 and rd.score_steps(fixed) == []
    assert fixed.dropna(subset=["scoreHome"]).iloc[-1][["scoreAway", "scoreHome"]].tolist() == [125, 124]
    # DEN at UTA, 2026-10-06: the plays do not reach NBA.com's quarter scores, so nothing is recomputed.
    monkeypatch.setattr(rd, "BULLS", 1610612743)
    with pytest.raises(rd.NotReady, match="does not match NBA.com's line score"):
        rd.build("0012600027")


def test_incomplete_four_factors_hold_until_the_deadline_then_use_the_box_score(monkeypatch):
    # MIN at MIA, 2026-10-10: NBA.com's four factors stopped at 203 of 240 team-minutes.
    monkeypatch.setattr(rd, "BULLS", 1610612750)
    g = game_dir("0012600002")
    assert rd.ff_minutes_short(rd.read(g, "ff_team.csv"), rd.read(g, "teams.csv")) == "203 of 240 minutes"
    with pytest.raises(rd.NotReady, match="cover 203 of 240 minutes"):
        rd.build("0012600002")
    monkeypatch.setattr(rd, "FALLBACK", True)
    d = rd.build("0012600002")
    assert d["four_factors"]["source"] == "box" and d["flow"]["nba_check"] == "match"
    assert d["four_factors"]["rows"][0][1:3] == [55.2, 54.3] and d["four_factors"]["rows"][1][1:3] == [None, None]
    # A complete feed never falls back, deadline or not.
    g = game_dir("0012600030")
    assert rd.ff_minutes_short(rd.read(g, "ff_team.csv"), rd.read(g, "teams.csv")) == ""


def test_play_by_play_shots_match_the_shot_feed_on_every_saved_game():
    # The shot chart's fallback: same attempts, locations, results, 2 or 3 points and shot types (1,220 shots).
    games = [p for p in sorted((game_dir("0022500084").parent).iterdir()) if p.name.startswith("002")]
    games += [game_dir("0012600030"), game_dir("0012600037")]
    matched = 0
    for g in games:
        raw, teams = rd.read(g, "shots_raw_chi.csv"), rd.read(g, "teams.csv")
        ours = rd.shots_from_pbp(rd.read(g, "pbp.csv"), int(raw.TEAM_ID.iloc[0]))
        assert len(ours) == int(teams.loc[teams.teamId == raw.TEAM_ID.iloc[0], "fieldGoalsAttempted"].iloc[0]), g.name
        m = ours.merge(raw, on="GAME_EVENT_ID", suffixes=("", "_nba"))
        for col in ("LOC_X", "LOC_Y", "SHOT_MADE_FLAG", "SHOT_TYPE", "ACTION_TYPE", "PLAYER_ID"):
            assert (m[col] == m[f"{col}_nba"]).all(), (g.name, col)
        matched += len(m)
    assert matched == 1220


def test_an_incomplete_shot_feed_waits_then_draws_from_the_play_by_play(monkeypatch):
    monkeypatch.setattr(rd, "BULLS", 1610612750)
    monkeypatch.setattr(rd, "FALLBACK", True)
    d = rd.build("0012600002")  # MIN at MIA: NBA.com's shot feed held 72 of the box score's 87 attempts
    assert d["shots_source"] == "pbp" and d["shots_complete"]
    assert sum(r[2] for r in d["shot_types"]) == 87 and sum(r[1] for r in d["shot_types"]) == 41
    assert (game_dir("0012600002") / "shots_chi_pbp.csv").exists()
    monkeypatch.setattr(rd, "FALLBACK", False)
    with pytest.raises(rd.NotReady):
        rd.build("0012600002")
    assert not (game_dir("0012600002") / "shots_chi_pbp.csv").exists()  # a complete or waiting build leaves none


def espn_check(game_id):
    """espn_check.check on the game's saved ESPN snapshot, offline: (values compared, differences, notes)."""
    import json
    import espn_check as ec
    g = game_dir(game_id)
    compared, found = ec.check(g, json.loads((g / "espn_summary.json").read_text()))
    return compared, [f for f in found if not f.startswith("note: ")], [f for f in found if f.startswith("note: ")]


def test_espn_check_agrees_on_a_clean_game_and_reads_both_sites_conventions():
    # CHI at DEN (2025-26): ESPN files points off turnovers under the team that turned it over and left lead
    # changes blank; neither is a difference. The heave on ESPN's play-by-play only is a note.
    compared, diffs, notes = espn_check("0022500248")
    assert compared > 1000 and diffs == []
    assert "note: ESPN does not publish CHI lead changes for this game; not compared" in notes
    assert any("Pickett (missed 3) is a heave" in n for n in notes)


def test_espn_check_flags_the_partial_shot_feed_and_agrees_on_starters():
    # MIN at MIA (Oct 10): NBA.com's game-night shot feeds stopped at 203 of 240 team-minutes and a re-entered
    # and-one broke its running score; ESPN had every shot. NBA.com marked six Memphis starters (Oct 9) and six
    # Cleveland and seven Orlando ones; the five on the floor at the tip match ESPN's.
    _, diffs, _ = espn_check("0012600002")
    assert sum("is on ESPN but not in NBA.com's shot feed" in d for d in diffs) >= 20
    assert "MIA running score parts at scoring play 41: NBA.com reaches 83 (Q3 1:13), ESPN 82 (Q3 1:13)" in diffs
    assert not any("started" in d for d in diffs)
    assert espn_check("0012600037")[1] == []
    assert espn_check("0012600041")[1] == []


def test_espn_check_names_a_changed_number(tmp_path):
    import json
    import shutil
    import espn_check as ec
    for f in game_dir("0012600037").iterdir():
        if f.is_file():
            shutil.copy(f, tmp_path / f.name)
    players = pd.read_csv(tmp_path / "players.csv")
    players.loc[players.familyName == "Wilson", "assists"] += 1
    players.to_csv(tmp_path / "players.csv", index=False)
    _, found = ec.check(tmp_path, json.loads((tmp_path / "espn_summary.json").read_text()))
    assert "CHI Wilson AST: NBA.com 1, ESPN 0" in found


def test_espn_names_match_across_suffixes_and_accents():
    import espn_check as ec
    assert ec.name_key("Brandon Boston") == ec.name_key("Brandon Boston Jr.")
    assert ec.name_key("Nikola Jović") == ec.name_key("Nikola Jovic")
    assert ec.name_key("PJ Washington") == ec.name_key("P.J. Washington")
    assert ec.clock_seconds("10:35") == 635 and ec.clock_seconds("45.2") == 45


def test_watcher_passes_the_espn_summary_not_each_difference():
    w = Watcher()
    assert w.feed("espn differs: MEM Post started: NBA.com yes, ESPN no\n", 0) == []
    line = "espn check: 1161 values compared with ESPN event 401908940, 1 differ (NBA.com stays the source; Claude reviews each)"
    assert w.feed(line + "\n", 0) == [line]


def test_no_picks_file_means_the_standard_recap():
    # Most nights the user sends no picks: no picks.json, and the build picks #mvp by Game Score as always.
    assert rd.picks(game_dir("0022500943")) == {}
    assert rd.build("0022500943")["awards"][0][2] == "Matas Buzelis"


def test_picks_set_the_mvp_drop_an_award_and_label_a_scoring_play(monkeypatch):
    gid = "0022500943"
    giddey = next(a[1] for a in rd.build(gid)["awards"] if a[0] == "#tripledouble")
    play = pbp(gid).query("actionType == 'Made Shot'").iloc[10]
    monkeypatch.setattr(rd, "picks", lambda g: {"mvp": giddey, "drop_awards": ["#closer"],
                                                "moments": [{"action": int(play.actionNumber), "label": "A picked play"}]})
    d = rd.build(gid)
    assert d["awards"][0][:2] == ["#mvp", giddey]
    assert "#closer" not in [a[0] for a in d["awards"]]
    note = next(n for n in d["flow"]["notes"] if n["kind"] == "moment")
    assert note["label"] == "A picked play" and [round(note["t"], 2), note["m"]] in d["flow"]["series"]


def test_early_pages_need_only_the_first_wave_of_feeds(monkeypatch):
    # Four factors, misc and the Bulls shot feed publish last; early pages are drawn without them.
    late = {"ff_team.csv", "misc_teams.csv", "shots_raw_chi.csv"}
    read = rd.read
    monkeypatch.setattr(rd, "read", lambda g, name, **kw: pd.DataFrame() if name in late else read(g, name, **kw))
    monkeypatch.setattr(rd, "EARLY", True)
    d = rd.build("0022500943")
    assert d["pending"] == ["Team stats", "Shot chart", "Game breakdown"]
    assert d["four_factors"] is None and d["h2h"] is None and d["awards"] == []
    assert d["flow"]["nba_check"] == "match"  # the first-wave checks still run
