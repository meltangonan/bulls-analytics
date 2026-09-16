"""Formatting, layout-guard and reconciliation checks for the Taj Gibson post."""
from pathlib import Path

import pandas as pd
import pytest

from scripts.prototypes import taj_gibson_retirement_data as data_post
from scripts.prototypes import taj_gibson_retirement_tables as tables


Column = tables.Column


def test_percentage_drops_the_leading_zero():
    # Basketball Reference's grammar, and the column widths are sized for it.
    assert tables._pct(0.49478) == ".495"
    assert tables._pct(0.421) == ".421"


@pytest.mark.parametrize("value,expected", [
    (1, "1st"), (2, "2nd"), (3, "3rd"), (5, "5th"), (10, "10th"),
    (11, "11th"), (12, "12th"), (13, "13th"), (22, "22nd"), (26, "26th"), (53, "53rd"),
])
def test_ordinals_handle_the_teens_and_the_twenties(value, expected):
    assert tables._ordinal(value) == expected


def test_a_cell_wider_than_its_column_is_refused(tmp_path):
    """The layout guard's reason for existing.

    Font sizes are points while the axes are pixels, so an eyeballed column
    width can render collided text that still saves happily. A first cut of
    this post shipped '2009-10' and '82' overlapping into '2009-1082'.
    """
    with pytest.raises(ValueError, match="too narrow"):
        tables._draw_table(
            [Column("SEASON", 40, "left")],
            [["2009-10"]],
            output_path=tmp_path / "overflow.png",
        )
    assert not (tmp_path / "overflow.png").exists()


def test_a_cell_inside_its_column_is_drawn(tmp_path):
    out = tables._draw_table(
        [Column("SEASON", 260, "left"), Column("G", 120)],
        [["2009-10", "82"]],
        output_path=tmp_path / "fits.png",
    )
    assert out.exists()


def test_adjacent_columns_keep_a_gap_between_their_text(tmp_path):
    """A right-aligned column must not butt against a left-aligned one.

    Both used to anchor on the same coordinate, so a count beside a label
    rendered as '74Double-doubles' while every cell still fit its own column.
    The inset is what separates them, so assert the anchors, not the pixels.
    """
    columns = [Column("N", 200), Column("LABEL", 400, "left")]
    right_x, right_align = tables._anchor_for(columns, 0)
    left_x, left_align = tables._anchor_for(columns, 1)
    assert (right_align, left_align) == ("right", "left")
    # The right-aligned cell ends before the left-aligned one starts.
    assert right_x < left_x
    assert left_x - right_x == pytest.approx(tables.CELL_PAD * 2)


def test_stripe_and_highlight_stay_distinguishable():
    """The band and the emphasis must not be two strengths of one colour.

    An earlier cut used pale pink for both, so on the striped table a top-10
    row stopped reading as special. The stripe is now a translucent neutral
    grey and the highlight a solid pale red: different hue, different opacity.
    """
    assert tables.STRIPE_FILL != tables.HIGHLIGHT_FILL
    assert tables.STRIPE_ALPHA < 1.0
    # A translucent grey darkens any ground by the same relative amount, which
    # a solid fill tuned for one Canva background cannot do.
    assert tables.STRIPE_FILL == tables.ROW_RULE


def test_the_rank_table_renders(tmp_path):
    data = data_post.DEFAULT_OUT / "franchise-ranks.csv"
    if not data.exists():
        pytest.skip("Run taj_gibson_retirement_data.py first.")
    assert tables.render_franchise_ranks(data, tmp_path / "ranks.png").exists()


def test_games_won_counts_results_not_a_rating():
    """'Games won' is the team's record in his games, not the Win Shares metric.

    The distinction matters on a published page: Win Shares is an established
    advanced statistic, and a row labelled like one but computed from wins
    would misrepresent both.
    """
    frame = _games([
        ("Taj Gibson", "2013-12-02", "CHI vs. NOP", "W", "2013–14", 8, 4, 1, 3, 0, 0, 1, 20.0, 6.0, 50.0),
        ("Taj Gibson", "2013-12-04", "CHI @ CLE", "W", "2013–14", 9, 5, 2, 3, 0, 0, 0, 21.0, 6.5, 52.0),
        ("Taj Gibson", "2013-12-06", "CHI @ DET", "L", "2013–14", 7, 3, 1, 2, 0, 0, 0, 19.0, 5.0, 48.0),
    ])
    milestones = data_post._milestones(frame).set_index("milestone")
    assert milestones.loc["Games won", "games"] == 2
    assert milestones.loc["Games won", "share"] == pytest.approx(2 / 3)


def test_an_overlong_footnote_line_is_refused(tmp_path):
    with pytest.raises(ValueError, match="Footnote lines"):
        tables._draw_table(
            [Column("CATEGORY", 300, "left")],
            [["Points"]],
            output_path=tmp_path / "footnote.png",
            footnote=("A footnote far too long to sit inside three hundred pixels of table",),
        )


def _splits(per_game_rows, total_rows):
    columns = ["TEAM_ABBREVIATION", "SEASON_ID", "GP", "GS", "MIN", "PTS", "REB",
               "OREB", "BLK", "FG_PCT", "FGM", "FGA"]
    return (pd.DataFrame(per_game_rows, columns=columns),
            pd.DataFrame(total_rows, columns=columns))


def test_career_row_weights_by_games_rather_than_averaging_seasons():
    """A 10-game season must not count as much as a 90-game one.

    Averaging the per-game rows would give 15.0 points here; the honest career
    figure is 1,100 points over 100 games.
    """
    per_game, totals = _splits(
        [("CHI", "2009-10", 10, 0, 10.0, 20.0, 5.0, 2.0, 1.0, 0.500, 8.0, 16.0),
         ("CHI", "2010-11", 90, 0, 10.0, 10.0, 5.0, 2.0, 1.0, 0.400, 4.0, 10.0)],
        [("CHI", "2009-10", 10, 0, 100.0, 200.0, 50.0, 20.0, 10.0, 0.500, 80.0, 160.0),
         ("CHI", "2010-11", 90, 0, 900.0, 900.0, 450.0, 180.0, 90.0, 0.400, 360.0, 900.0)],
    )
    table = data_post._season_table(per_game, totals, "regular")
    career = table[table["is_career"]].iloc[0]
    assert career.games == 100
    assert career.points == pytest.approx(11.0)
    # FG% is recomputed from made over attempted, never averaged from the rates.
    assert career.fg_pct == pytest.approx(440.0 / 1060.0)


def test_only_chicago_stints_reach_the_season_table():
    per_game, totals = _splits(
        [("CHI", "2009-10", 10, 0, 10.0, 20.0, 5.0, 2.0, 1.0, 0.500, 8.0, 16.0),
         ("OKC", "2016-17", 23, 0, 20.0, 9.0, 6.0, 2.0, 1.0, 0.500, 4.0, 8.0)],
        [("CHI", "2009-10", 10, 0, 100.0, 200.0, 50.0, 20.0, 10.0, 0.500, 80.0, 160.0),
         ("OKC", "2016-17", 23, 0, 460.0, 207.0, 138.0, 46.0, 23.0, 0.500, 92.0, 184.0)],
    )
    table = data_post._season_table(per_game, totals, "regular")
    assert list(table.loc[~table["is_career"], "season"]) == ["2009-10"]
    assert table[table["is_career"]].iloc[0].games == 10


def _games(rows):
    """Player-game rows with the columns the post's builders read.

    The boxed leaderboard shows made-attempted splits and plus-minus, so those
    columns travel with every fixture even when a given test ignores them.
    """
    columns = ["player", "game_date", "matchup", "result", "season", "points", "reb",
               "oreb", "dreb", "ast", "stl", "blk", "minutes", "game_score", "ts_pct"]
    extra = ["fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "tov", "plus_minus"]
    frame = pd.DataFrame(rows, columns=columns)
    for column in extra:
        if column not in frame:
            frame[column] = 0
    if "game_id" not in frame:
        # A regular-season id unless the row is explicitly a playoff fixture;
        # the boxed rows read this to derive their round and game marker.
        frame["game_id"] = [
            "0041300134" if str(d) == "2014-04-27" else "0021300257"
            for d in frame["game_date"]
        ]
    return frame


def test_career_highs_report_a_tie_count_on_every_row():
    """Tie counts appear even when the answer is one.

    Showing '3 times' only where it flatters him and hiding it elsewhere would
    misrepresent which highs were one-offs.
    """
    frame = _games([
        ("Taj Gibson", "2013-12-02", "CHI vs. NOP", "L", "2013–14", 26, 14, 4, 10, 0, 0, 5, 44.0, 25.2, 57.7),
        ("Taj Gibson", "2014-01-22", "CHI @ CLE", "W", "2013–14", 26, 5, 1, 4, 2, 1, 3, 43.0, 24.3, 73.7),
        ("Taj Gibson", "2013-02-02", "CHI @ ATL", "W", "2012–13", 19, 19, 6, 13, 2, 1, 3, 45.0, 23.4, 62.0),
    ])
    highs = data_post._career_highs(frame, _games([])).set_index("category")
    assert highs.loc["Points", "value"] == 26
    assert highs.loc["Points", "times"] == 2
    # The named game is the best of the tied nights, not the first one seen.
    assert highs.loc["Points", "game_date"] == "2013-12-02"
    assert highs.loc["Rebounds", "times"] == 1


def test_a_playoff_night_can_set_the_career_high():
    """The postseason counts toward a career high, because it is the career.

    His best scoring night as a Bull was 32 at Washington in the 2014 first
    round. A slide that reported the regular-season 26 as his career high
    would be plainly wrong, so the high is taken across both season types and
    the row records which one set it.
    """
    regular = _games([
        ("Taj Gibson", "2013-12-02", "CHI vs. NOP", "L", "2013–14", 26, 14, 4, 10, 0, 0, 5, 44.0, 25.2, 57.7),
    ])
    playoffs = _games([
        ("Taj Gibson", "2014-04-27", "CHI @ WAS", "L", "2013–14", 32, 7, 3, 4, 1, 1, 1, 32.0, 27.5, 83.9),
    ])
    highs = data_post._career_highs(regular, playoffs).set_index("category")
    assert highs.loc["Points", "value"] == 32
    assert bool(highs.loc["Points", "in_playoffs"]) is True
    # The regular-season figure is kept alongside so the page can say which
    # highs the postseason actually moved.
    assert highs.loc["Points", "regular_season_value"] == 26
    # Rebounds peaked in the regular season, so that row is unaffected.
    assert highs.loc["Rebounds", "value"] == 14
    assert bool(highs.loc["Rebounds", "in_playoffs"]) is False


def test_top_games_rank_playoffs_alongside_the_regular_season():
    regular = _games([
        ("Taj Gibson", "2013-12-02", "CHI vs. NOP", "L", "2013–14", 26, 14, 4, 10, 0, 0, 5, 44.0, 25.2, 57.7),
    ])
    playoffs = _games([
        ("Taj Gibson", "2014-04-27", "CHI @ WAS", "L", "2013–14", 32, 7, 3, 4, 1, 1, 1, 32.0, 27.5, 83.9),
    ])
    best = data_post._top_games(regular, playoffs, count=2)
    assert list(best["rank"]) == [1, 2]
    assert best.iloc[0].season_type == "Playoffs"
    assert best.iloc[0].opponent == "at WAS"
    assert best.iloc[1].opponent == "vs NOP"


def _ranks(rows):
    return pd.DataFrame(
        rows, columns=["category", "stat", "total", "rank", "pool", "partial_coverage"]
    )


def test_reconcile_rejects_a_franchise_total_that_moved():
    ranks = _ranks([("Points", "PTS", 5279, 26, 439, False),
                    ("Games played", "GP", 562, 10, 439, False),
                    ("Total rebounds", "REB", 3586, 12, 439, False),
                    ("Blocks", "BLK", 695, 5, 401, True)])
    with pytest.raises(ValueError, match="PTS"):
        data_post._reconcile(ranks, _games([]), _games([]), pd.DataFrame())


def test_reconcile_rejects_game_logs_that_disagree_with_the_franchise_totals():
    """Two independent sources must reproduce the same career line.

    The cached logs and FranchisePlayers are fetched separately, so a silent
    change in either one has to fail loudly rather than reach a published page.
    """
    ranks = _ranks([("Points", "PTS", 5280, 26, 439, False),
                    ("Games played", "GP", 562, 10, 439, False),
                    ("Total rebounds", "REB", 3586, 12, 439, False),
                    ("Blocks", "BLK", 695, 5, 401, True)])
    short = _games([
        ("Taj Gibson", "2013-12-02", "CHI vs. NOP", "L", "2013–14", 26, 14, 4, 10, 0, 0, 5, 44.0, 25.2, 57.7),
    ])
    with pytest.raises(ValueError, match="Cached game logs"):
        data_post._reconcile(ranks, short, _games([]), pd.DataFrame())


def test_published_data_matches_the_verified_figures():
    """Guards the five CSVs the renderer actually reads."""
    data_dir = data_post.DEFAULT_OUT
    if not (data_dir / "franchise-ranks.csv").exists():
        pytest.skip("Run taj_gibson_retirement_data.py to build the tables first.")

    ranks = pd.read_csv(data_dir / "franchise-ranks.csv").set_index("stat")
    assert ranks.loc["PTS", "total"] == 5280
    assert ranks.loc["BLK", "rank"] == 5
    assert ranks.loc["OREB", "rank"] == 6
    assert ranks.loc["GP", "rank"] == 10
    # Points leads the table and games played closes it.
    ordered = pd.read_csv(data_dir / "franchise-ranks.csv")["stat"].tolist()
    assert ordered[0] == "PTS" and ordered[-1] == "GP"
    # Fouls and turnovers were deliberately cut.
    assert "PF" not in ordered and "TOV" not in ordered
    # Partial-coverage rows are exactly the four the NBA began tracking in 1973-74.
    partial = set(pd.read_csv(data_dir / "franchise-ranks.csv")
                  .query("partial_coverage")["stat"])
    assert partial == {"OREB", "DREB", "STL", "BLK"}

    regular = pd.read_csv(data_dir / "season-regular.csv")
    assert int(regular.loc[~regular["is_career"], "games"].sum()) == 562
    assert int(regular[regular["is_career"]].iloc[0].starts) == 229

    playoffs = pd.read_csv(data_dir / "season-playoffs.csv")
    assert int(playoffs.loc[~playoffs["is_career"], "games"].sum()) == 56

    # Made-versus-attempted is spelled out so no row is ambiguous.
    labels = pd.read_csv(data_dir / "franchise-ranks.csv")["category"].tolist()
    assert "Field goals made" in labels and "Free throws made" in labels

    highs = pd.read_csv(data_dir / "career-highs.csv").set_index("category")
    # 32 at Washington in the 2014 playoffs, not the regular-season 26.
    assert highs.loc["Points", "value"] == 32
    assert bool(highs.loc["Points", "in_playoffs"]) is True
    assert highs.loc["Points", "regular_season_value"] == 26
    assert highs.loc["Rebounds", "value"] == 19
    assert highs.loc["Blocks", "times"] == 4
    assert highs.loc["Defensive rebounds", "value"] == 13
    # Points is the only category the postseason moved.
    assert list(highs.loc[highs["in_playoffs"]].index) == ["Points"]
    # Fouls were cut: a high reached 21 times is a ceiling, not a highlight.
    # Minutes were cut too: it describes a rotation, not a performance.
    assert "Personal fouls" not in highs.index
    assert "Minutes" not in highs.index
    # Every career-high category needs a box-score code for the strip layout.
    assert set(highs.index) <= set(tables.HIGH_CODES)
    # Eight categories fills the four-wide grid exactly, with no empty cell.
    assert len(highs) == 8 and len(highs) % 4 == 0
    assert highs.loc["Plus-minus", "value"] == 35

    milestones = pd.read_csv(data_dir / "milestones.csv").set_index("milestone")
    assert milestones.loc["Double-doubles", "games"] == 74
    assert milestones.loc["15-rebound games", "games"] == 10
    assert milestones.loc["5+ block games", "games"] == 15
    assert milestones.loc["5+ offensive rebound games", "games"] == 72
    # Team record in his games, not the Win Shares metric.
    assert milestones.loc["Games won", "games"] == 337
    assert milestones.loc["Games won", "share"] == pytest.approx(337 / 562)
    # Rates dressed as milestones were cut: at 67% and 87% these restated his
    # per-game averages, which the season tables already carry.
    assert "Games with a block" not in milestones.index
    assert "Games with an offensive rebound" not in milestones.index
    # Shares are derived from the same denominator the footnote prints.
    assert (milestones["of_games"] == 562).all()
    assert milestones.loc["Double-doubles", "share"] == pytest.approx(74 / 562)

    top = pd.read_csv(data_dir / "top-games.csv")
    assert len(top) == 5
    assert top.iloc[0].game_score == pytest.approx(27.5)
    assert top.iloc[0].season_type == "Playoffs"
    assert top["game_score"].is_monotonic_decreasing
    # The boxed leaderboard prints the whole line, not just derived rates.
    assert {"fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "tov", "plus_minus"} <= set(top.columns)
    assert top.iloc[0].fgm == 13 and top.iloc[0].fga == 16
    # He attempted no threes in any of his five best games.
    assert (top["fg3a"] == 0).all()


def test_a_differential_career_high_is_signed():
    """+35 is a margin, not a count, and reads wrong without its sign."""
    row = pd.Series({"category": "Plus-minus", "value": 35.0})
    assert tables._high_value(row) == "+35"
    assert tables._high_value(pd.Series({"category": "Points", "value": 32.0})) == "32"


def test_the_hero_value_carries_no_colour_scale():
    """The Game Score box is house red, not a heat fill.

    An earlier cut coloured it from the settled interpretation bands. All five
    of his best nights land inside one band, so the scale painted every box
    identically while implying a comparison it never made.
    """
    assert not hasattr(tables, "game_score_fill")
    assert not hasattr(tables, "GAME_SCORE_BANDS")


def test_his_best_games_all_sit_in_one_interpretation_band():
    """Between 20 and 30: very good nights, not star-level ones.

    Worth pinning because it is the reason the hero box needs no scale.
    """
    data = data_post.DEFAULT_OUT / "top-games.csv"
    if not data.exists():
        pytest.skip("Run taj_gibson_retirement_data.py first.")
    assert pd.read_csv(data)["game_score"].between(20, 30).all()


def test_the_table_treatment_uses_the_shared_accent_card(tmp_path, monkeypatch):
    """The hero column reuses house.draw_accent_card, not a local rectangle.

    The card's geometry, rounding and shadow are the settled house format the
    2025-26 best-games post uses; redrawing it here by hand would drift away
    from that the first time either side changed.
    """
    data = data_post.DEFAULT_OUT / "top-games.csv"
    if not data.exists():
        pytest.skip("Run taj_gibson_retirement_data.py first.")

    calls = []
    original = tables.house.draw_accent_card

    def spy(*args, **kwargs):
        calls.append(args)
        return original(*args, **kwargs)

    monkeypatch.setattr(tables.house, "draw_accent_card", spy)
    assert tables.render_top_games(data, tmp_path / "table.png").exists()
    # One card spanning all five rows, not one card per row.
    assert len(calls) == 1 and calls[0][4] == 5


def test_the_table_treatment_drops_the_three_point_and_free_throw_splits():
    """He attempted no threes in any of these games.

    An all-zero 3PT column and a free-throw split cost width without telling
    the reader anything the points column has not already.
    """
    labels = [label for label, _, _ in tables.TABLE_STATS]
    assert "3PT" not in labels and "FT" not in labels
    assert labels == ["PTS", "FG", "REB", "AST", "STL", "BLK", "TOV", "+/-"]


@pytest.mark.parametrize("game_id,expected", [
    # The game-score-by-height post hand-kept this one as "(RD 2 GM3)";
    # deriving it reproduces that exactly, which is what validates the parse.
    ("0041000203", "(RD 2 GM3)"),
    ("0041300134", "(RD 1 GM4)"),   # Taj's 32 at Washington, 2014 first round
    ("0041000301", "(RD 3 GM1)"),   # the 2011 conference finals opener
    ("0021300257", ""),             # regular season carries no marker
])
def test_playoff_round_and_game_come_from_the_game_id(game_id, expected):
    assert data_post.playoff_label(game_id) == expected


def test_playoff_label_survives_an_unpadded_id():
    """Pandas reads game ids as integers, dropping the leading zero."""
    assert data_post.playoff_label(41300134) == "(RD 1 GM4)"


def test_the_top_games_table_renders(tmp_path):
    data = data_post.DEFAULT_OUT / "top-games.csv"
    if not data.exists():
        pytest.skip("Run taj_gibson_retirement_data.py first.")
    assert tables.render_top_games(data, tmp_path / "top-games.png").exists()


# ------------------------------------------------------------------ shot diet

def test_unlabelled_league_rows_are_dropped_not_placed():
    """A zone NBA.com never assigned is unavailable, not derivable.

    Older league seasons carry tens of unlabelled rows per ~200,000; the modern
    ones carry none, which is why the rest of the zone-chart family never meets
    them. They leave the baseline rather than being placed by coordinate.
    """
    from scripts.prototypes import taj_gibson_bulls_zone_charts as zones
    league = pd.DataFrame({
        "loc_x": [0, 10, 20],
        "loc_y": [0, 10, 20],
        "shot_zone": ["Restricted Area", None, "Mid-Range"],
    })
    kept = zones.drop_unlabelled_league_rows(league, "2015-16")
    assert len(kept) == 2
    assert kept["shot_zone"].notna().all()


def test_a_frame_with_no_zone_column_passes_through():
    from scripts.prototypes import taj_gibson_bulls_zone_charts as zones
    league = pd.DataFrame({"loc_x": [0], "loc_y": [0]})
    assert len(zones.drop_unlabelled_league_rows(league, "2015-16")) == 1


def test_shot_diet_keeps_families_he_never_used():
    """An untaken shot type is the finding, not a row to drop.

    ``family_shares`` returns every family including zeros, so the rendered
    slide cannot silently close a gap in his diet.
    """
    from scripts.prototypes import taj_gibson_bulls_zone_charts as zones
    shots = pd.DataFrame({
        "ACTION_TYPE": ["Jump Shot", "Layup Shot", "Dunk Shot", "Jump Shot"],
        "SHOT_MADE_FLAG": [0, 1, 1, 1],
    })
    diet = zones.shot_diet(shots)
    assert set(diet["family"]) == set(tables_families().FAMILIES)
    assert diet.loc[diet.family.eq("Step-backs"), "fga"].iloc[0] == 0
    assert diet["share_pct"].sum() == pytest.approx(100.0)


def tables_families():
    from bulls.analysis import shot_families
    return shot_families


def test_published_shot_diet_reconciles_to_the_franchise_total():
    data = data_post.DEFAULT_OUT / "shot-diet.csv"
    if not data.exists():
        pytest.skip("Run taj_gibson_bulls_zone_charts.py to build the shot diet.")
    diet = pd.read_csv(data)
    # Every one of his Bulls field-goal attempts is labelled and accounted for.
    assert int(diet["fga"].sum()) == 4408
    # The CSV stores shares to four decimals, so the round-trip sum lands a
    # ten-thousandth off 100. The attempt count above is the exact check.
    assert diet["share_pct"].sum() == pytest.approx(100.0, abs=0.01)
    by_family = diet.set_index("family")
    assert by_family.loc["Dunks", "fga"] == 547
    # The unlabelled default is the largest family, which the slide has to say.
    assert by_family["fga"].idxmax() == "Standard jumpers"
    # Thin families carry no rate.
    assert not bool(by_family.loc["Step-backs", "rated"])


def test_the_diet_slide_renders(tmp_path):
    data = data_post.DEFAULT_OUT / "shot-diet.csv"
    if not data.exists():
        pytest.skip("Run taj_gibson_bulls_zone_charts.py to build the shot diet.")
    assert tables.render_shot_diet(data, tmp_path / "diet.png").exists()







def test_only_the_shipped_slides_remain():
    """The registry is the post, so a cut treatment must leave it.

    Several alternates were built and rejected (a rank dot plot, a boxed-card
    leaderboard, a career-high card grid and table, a banded rank table, pie
    and 100% bar shot diets). Their renders stay in the asset history; their
    renderers do not, so nothing can quietly re-enter the carousel.
    """
    assert sorted(tables.SLIDES) == [
        "career-high-grid", "career-high-strip", "franchise-ranks", "milestones",
        "playoffs", "regular-season", "shot-diet", "top-games-table",
    ]
    for gone in ("render_top_games_boxed", "render_career_high_cards",
                 "render_career_highs", "render_shot_diet_pie",
                 "render_shot_diet_stack", "_diet_grouped"):
        assert not hasattr(tables, gone), gone


def test_career_high_values_carry_no_colour():
    """Every figure on the number-and-stat slides is house black.

    The playoff-set high was red for a while; it is now stated in the note
    instead, so no reader has to work out what a colour meant.
    """
    source = Path(tables.__file__).read_text()
    grid = source[source.index("def render_career_high_grid("):]
    grid = grid[:grid.index("# ---")] if "# ---" in grid else grid
    assert "RED if" not in grid


# ------------------------------------------------------ season-best marking

def _season_frame(rows):
    columns = ["season", "games", "starts", "minutes", "points", "rebounds",
               "offensive_rebounds", "blocks", "fg_pct", "is_career"]
    return pd.DataFrame(rows, columns=columns)


def test_a_tied_season_best_marks_every_tied_row():
    """Both 2.8s get marked, not an arbitrary one of them.

    NBA.com publishes per-game figures already rounded to a tenth, so two
    seasons can be genuinely tied at the only precision available. Marking one
    of two identical printed numbers would read as a mistake to anyone looking
    down the column.
    """
    frame = _season_frame([
        ("2009-10", 82, 70, 26.9, 9.0, 7.5, 2.8, 1.3, 0.494, False),
        ("2015-16", 73, 55, 26.5, 8.6, 6.9, 2.8, 1.1, 0.526, False),
        ("Bulls career", 155, 125, 26.7, 8.8, 7.2, 2.8, 1.2, 0.509, True),
    ])
    marked = tables.season_best_cells(frame)
    orb_column = 6
    assert (0, orb_column) in marked
    assert (1, orb_column) in marked


def test_the_career_row_is_never_a_season_best():
    """It is an average of the rows above it, not a season of its own."""
    frame = _season_frame([
        ("2009-10", 82, 70, 26.9, 9.0, 7.5, 2.8, 1.3, 0.494, False),
        ("Bulls career", 82, 70, 99.9, 99.9, 99.9, 99.9, 9.9, 0.999, True),
    ])
    marked = tables.season_best_cells(frame)
    assert all(row_index != 1 for row_index, _ in marked)


def test_counts_are_not_eligible_for_the_season_best_mark():
    """Games and games started are counts, not per-game rates."""
    eligible = {index for _, index, _ in tables.SEASON_BEST_COLUMNS}
    season_column, games_column, starts_column = 0, 1, 2
    assert not eligible & {season_column, games_column, starts_column}
    assert eligible == {3, 4, 5, 6, 7, 8}


def test_published_season_tables_mark_his_peak_year():
    data_dir = data_post.DEFAULT_OUT
    if not (data_dir / "season-regular.csv").exists():
        pytest.skip("Run taj_gibson_retirement_data.py first.")
    regular = pd.read_csv(data_dir / "season-regular.csv")
    marked = tables.season_best_cells(regular)
    peak = regular.index[regular.season.eq("2013-14")][0]
    # 2013-14 was his best scoring and heaviest-minutes season.
    assert (int(peak), 4) in marked and (int(peak), 3) in marked
    # The two known ties are both marked, four cells across two columns.
    assert sum(1 for _, column in marked if column == 6) == 2
    assert sum(1 for _, column in marked if column == 7) == 2
