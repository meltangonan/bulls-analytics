"""2025-26 Bulls share-of-points headshot grid."""
import pandas as pd

from scripts.prototypes import points_share_grid as grid


def test_player_points_reconcile_to_team_total():
    players = grid.prepare()
    assert players.PTS.sum() == grid.TEAM_TOTAL == 9537
    assert len(players) == 28


def test_largest_remainder_fills_exactly_100_squares():
    players = grid.prepare()
    assert players.SQUARES.sum() == 100
    # Every player's squares stay within one of their exact share.
    assert ((players.SQUARES - players.SHARE).abs() < 1).all()
    top = players.iloc[0]
    assert (top.PLAYER_NAME, top.SQUARES) == ("Matas Buzelis", 13)


def test_players_under_half_a_percent_are_the_hidden_five():
    players = grid.prepare()
    hidden = players[players.SQUARES == 0].PLAYER_NAME.map(grid.short_name)
    assert list(hidden) == ["Ivey", "Gueye", "E. Miller", "Flowers", "Essengue"]
    # McClung's 0.50% rounds up and Ivey's 0.48% rounds down: the 1% rule, not a tiebreak.
    assert players.set_index("PLAYER_NAME").loc["Mac McClung", "SQUARES"] == 1


def test_snake_fill_keeps_every_block_one_shape():
    players = grid.prepare()
    cells = grid.snake_cells(players[players.SQUARES > 0])
    assert sum(len(c) for c in cells.values()) == 100
    for block in cells.values():
        grid.outline(block)  # raises if a block is split


def test_outline_rejects_a_block_touching_only_at_a_corner():
    try:
        grid.outline({(0, 1), (1, 0)})
    except (ValueError, KeyError):
        return
    raise AssertionError("split block was accepted")


def test_two_millers_are_disambiguated():
    assert grid.short_name("Leonard Miller") == "L. Miller"
    assert grid.short_name("Emanuel Miller") == "E. Miller"
    assert grid.short_name("Nikola Vučević") == "Vučević"


def test_touching_blocks_never_share_a_tint():
    players = grid.prepare()
    blocks = grid.snake_cells(players[players.SQUARES > 0])
    owner = {cell: pid for pid, cells in blocks.items() for cell in cells}
    tints = grid.assign_tints(blocks, grid.TINTS)
    for (r, c), pid in owner.items():
        for nb in ((r + 1, c), (r, c + 1)):
            other = owner.get(nb)
            if other is not None and other != pid:
                assert tints[pid] != tints[other]


def test_player_points_reconcile_to_official_team_logs_game_by_game():
    team = pd.read_csv(grid.POST / "data" / "bulls_2025_26_team_game_logs.csv")
    players = pd.read_csv(grid.DATA)
    assert len(team) == 82 and team.PTS.sum() == grid.TEAM_TOTAL
    by_game = players.groupby("GAME_ID").PTS.sum()
    assert by_game.to_dict() == team.set_index("GAME_ID").PTS.to_dict()
