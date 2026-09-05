from pathlib import Path
from dataclasses import replace
import pandas as pd
import pytest
from scripts.prototypes.season_game_performances import prepare
from scripts.prototypes import top_game_performances as games

DATA = Path(__file__).resolve().parents[1] / 'docs/visuals/2026-09-05-top-game-score-2025-26/data'


def sources():
    return pd.read_csv(DATA / 'players-source.csv'), pd.read_csv(DATA / 'teams-source.csv')


def test_complete_season_reconciles_and_allows_repeat_players():
    *_, ranked = prepare(*sources())
    assert len(ranked) == 15
    assert ranked.iloc[0].player == 'Tre Jones'
    assert ranked.iloc[0].game_score == pytest.approx(34.5)
    assert ranked.head(10).player.eq('Josh Giddey').sum() == 5


def test_missing_entire_player_game_is_rejected():
    players, teams = sources()
    players = players.loc[players.game_id.ne(players.iloc[0].game_id)]
    with pytest.raises(ValueError, match='coverage'):
        prepare(players, teams)


def test_wrong_player_points_are_rejected():
    players, teams = sources()
    players.loc[0, 'points'] += 1
    with pytest.raises(ValueError, match='reconcile'):
        prepare(players, teams)


def test_fifteen_includes_exactly_the_next_five_games():
    *_, ranked = prepare(*sources())
    previous = pd.read_csv(DATA / "top-ten.csv")
    assert ranked.head(10).player_id.tolist() == previous.player_id.tolist()
    assert ranked.head(10).game_score.tolist() == pytest.approx(previous.game_score.tolist())
    assert ranked.game_score.is_monotonic_decreasing
    assert ranked["rank"].tolist() == list(range(1, 16))


def test_compact_table_can_render_turnovers_with_overlapping_headshots(tmp_path, monkeypatch):
    *_, ranked = prepare(*sources())
    monkeypatch.setattr(games, "OUT", tmp_path)
    monkeypatch.setattr(games, "ensure_headshots", lambda _: None)
    path = games.render_chart(
        ranked,
        "2026-09-05",
        decade="2025-26",
        show_free_throws=True,
        show_turnovers=True,
        top_n=15,
        layout=replace(
            games.DECADE_LAYOUT,
            row_height=96,
            headshot_x=52,
            name_x=112,
            headshot_half_size=52,
            headshot_rise=4,
            first_row_from_top=145,
            bottom_pad=42,
        ),
    )
    assert path.exists()
