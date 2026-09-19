"""Top fifteen Bulls rookie games since 2000–01 by Game Score, regular season and playoffs.

The Bulls game logs come from ``top_game_performances``' cached NBA.com sources. NBA.com's
Rookie filter (saved by the 2026-08-14 rookie landscape post) defines who was a rookie; the
CommonAllPlayers first season is an independent audit. A rookie's playoff games that season
share the pool, and repeat players are eligible. Renders the settled Game Score table and the
boxed card grammar of the 2026-08-25 Game Score by height post.
"""
from pathlib import Path
from dataclasses import replace
import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from nba_api.stats.endpoints import commonallplayers
from PIL import Image

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from bulls.data.fetch import _NBA_HEADERS
from bulls.graphics import house
from scripts.prototypes import height_ladder_cards as cards
from scripts.prototypes import top_game_performances as games
from scripts.prototypes.game_score_by_height import game_score_fill

DATA = ROOT / 'docs/visuals/2026-09-18-rookie-game-scores/data'
PORTRAITS = DATA / 'portraits'
ROOKIE_FILTER_ORIGIN = ROOT / 'docs/visuals/2026-08-14-bulls-rookie-landscape/data/nba-bulls-rookies-since-2000.csv'
ROOKIE_FILTER = DATA / 'nba-bulls-rookies-since-2000.csv'
FIRST_SEASONS = DATA / 'nba-common-all-players-first-seasons.csv'
SEASONS = range(2001, 2027)
LABEL = 'Rookies since 2000–01'
TOP_N = 15
# Taller rows than the 2025–26 table: the Canva page has room below the table at its width.
TABLE_LAYOUT = replace(games.DECADE_LAYOUT, row_height=108, headshot_x=60, name_x=128,
                       headshot_half_size=66, headshot_rise=8, first_row_from_top=145,
                       bottom_pad=42, name_font_size=21, context_font_size=12.5,
                       name_rise=16, context_drop=22)
PLAYOFF_SEASONS = {2005, 2006, 2007, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2017, 2022}
# CommonAllPlayers dates Randy Holcomb from his 2002 draft; his only NBA games were four
# Bulls games in 2005–06, which NBA.com's Rookie filter correctly treats as his rookie year.
KNOWN_FIRST_SEASON_DISAGREEMENTS = {(2006, 2450)}


def fetch_first_seasons(refresh=False):
    """Load NBA.com's CommonAllPlayers first-season field, fetching once when absent."""
    if FIRST_SEASONS.exists() and not refresh:
        return pd.read_csv(FIRST_SEASONS)
    frame = commonallplayers.CommonAllPlayers(
        is_only_current_season=0, headers=_NBA_HEADERS, timeout=60).get_data_frames()[0]
    return frame[['PERSON_ID', 'DISPLAY_FIRST_LAST', 'FROM_YEAR', 'TO_YEAR']]


def frame_like_cdn_headshot(portrait, *, height_fraction=0.76, top_fraction=0.02):
    """Place a tight head-and-shoulders cutout on a transparent 1040x760 CDN-shaped canvas.

    The table crops the top 74% of every headshot into a square. A tight cutout would fill that
    square edge to edge, so it is shrunk and centred until its head matches NBA.com's framing.
    """
    canvas = Image.new('RGBA', (1040, 760), (0, 0, 0, 0))
    height = round(760 * height_fraction)
    image = portrait.convert('RGBA').resize(
        (round(portrait.width * height / portrait.height), height), Image.LANCZOS)
    canvas.alpha_composite(image, ((1040 - image.width) // 2, round(760 * top_fraction)))
    return canvas


def use_post_portraits(player_ids):
    """Replace a missing or silhouette cached headshot with this post's hand-sourced portrait."""
    for player_id in {int(value) for value in player_ids}:
        portrait = PORTRAITS / f'{player_id}.png'
        cached = games.HEADSHOT_CACHE / f'{player_id}.png'
        if not portrait.exists():
            continue
        silhouette = cached.exists() and hashlib.md5(cached.read_bytes()).hexdigest().startswith(
            games.CDN_SILHOUETTE_MD5)
        if silhouette or not cached.exists() or cached.stat().st_mtime < portrait.stat().st_mtime:
            with Image.open(portrait) as source:
                frame_like_cdn_headshot(source).save(cached, format='PNG')


def playoff_context(game_id):
    """NBA.com playoff ids encode the round at digit 8 and the game at digit 10."""
    game_id = str(game_id).zfill(10)
    return f'(RD {game_id[7]} GM{game_id[9]})'


def validated_pool(players, teams, pool, seasons):
    """Build one season type's working table and prove complete, reconciled coverage."""
    players, teams = players.copy(), teams.copy()
    for frame in (players, teams):
        frame['game_id'] = frame['game_id'].astype(str).str.zfill(10)
    table = games.build_working_table(players, teams)
    if set(table.season_end_year) != set(seasons) or set(teams.season_end_year) != set(seasons):
        raise ValueError(f'{pool} coverage does not match the expected seasons.')
    if set(table.game_id) != set(teams.game_id):
        raise ValueError(f'{pool} player and team game coverage differs.')
    reconciliation = table.groupby(['season_end_year', 'game_id'], as_index=False).agg(
        player_points=('points', 'sum'), team_points=('team_points', 'first'))
    if not reconciliation.player_points.eq(reconciliation.team_points).all():
        raise ValueError(f'{pool} player points do not reconcile to team scores.')
    if not np.isfinite(table[['game_score', 'ts_pct']]).all().all():
        raise ValueError('Nonfinite derived metric.')
    table['pool'] = reconciliation['pool'] = pool
    table['context_note'] = table.game_id.map(playoff_context) if pool == 'Playoffs' else ''
    return table, reconciliation


def prepare(players, teams, playoff_players, playoff_teams, rookie_filter, first_seasons):
    table, reconciliation = validated_pool(players, teams, 'Regular season', SEASONS)
    playoffs, playoff_reconciliation = validated_pool(
        playoff_players, playoff_teams, 'Playoffs', PLAYOFF_SEASONS)

    played = set(zip(table.season_end_year, table.player_id))
    rookie_pairs = set(zip(rookie_filter.season.astype(int), rookie_filter.player_id.astype(int)))
    if not rookie_pairs <= played:
        raise ValueError('The Rookie filter names a player-season with no Bulls game rows.')
    first = first_seasons.set_index('PERSON_ID').FROM_YEAR
    if not {p for _, p in played} <= set(first.index):
        raise ValueError('A Bulls player is missing from CommonAllPlayers.')
    by_first_season = {(y, p) for y, p in played if int(first[p]) == y - 1}
    if rookie_pairs ^ by_first_season != KNOWN_FIRST_SEASON_DISAGREEMENTS:
        raise ValueError(f'Rookie sources disagree: {sorted(rookie_pairs ^ by_first_season)}.')

    season_games = table.groupby(['season_end_year', 'player_id']).size()
    rookie_audit = rookie_filter[['season', 'season_label', 'player_id', 'player_name', 'games']].copy()
    rookie_audit['bulls_game_rows'] = [season_games[(s, p)] for s, p in zip(rookie_audit.season, rookie_audit.player_id)]
    rookie_audit['common_all_players_from_year'] = rookie_audit.player_id.map(first)
    rookie_audit['first_season_agrees'] = [
        (s, p) in by_first_season for s, p in zip(rookie_audit.season, rookie_audit.player_id)]
    if not rookie_audit.games.eq(rookie_audit.bulls_game_rows).all():
        raise ValueError('Rookie filter games do not match Bulls game-log rows.')

    # Rookie status is a regular-season fact; that season's playoff games inherit it.
    pool = pd.concat([table, playoffs], ignore_index=True)
    pool['overtime_periods'] = pool.game_id.map(games.minute_reconciliation(pool).overtime_periods)
    rookies = pool.loc[[pair in rookie_pairs for pair in zip(pool.season_end_year, pool.player_id)]].copy()
    reconciliation = pd.concat([reconciliation, playoff_reconciliation], ignore_index=True)
    return pool, reconciliation, rookie_audit, rookies, select_top(rookies)


def select_top(rookies, top_n=TOP_N):
    """Rank rookie games by Game Score, then points, refusing a tie across the cutoff."""
    rookies = rookies.copy()
    # Every Game Score term is a multiple of 0.1; rounding strips float noise so an exact tie
    # falls through to the shared points tiebreak instead of an arbitrary 1e-15 difference.
    rookies['game_score'] = rookies.game_score.round(1)
    rookies['decade'] = LABEL
    ranked = games.top_games_by_decade(rookies, top_n=top_n + 1)
    if ranked.game_score.iloc[top_n - 1] == ranked.game_score.iloc[top_n]:
        raise ValueError('A Game Score tie crosses the top-fifteen cutoff.')
    return ranked.head(top_n)


def load_sources(refresh=False):
    def load(season_type):
        players = [games.fetch_bulls_season(y, season_type=season_type, refresh=refresh) for y in SEASONS]
        teams = [games.fetch_bulls_team_games(y, season_type=season_type, refresh=refresh) for y in SEASONS]
        return (pd.concat([f for f in players if len(f)], ignore_index=True),
                pd.concat([f for f in teams if len(f)], ignore_index=True))
    players, teams = load('Regular Season')
    playoff_players, playoff_teams = load('Playoffs')
    DATA.mkdir(parents=True, exist_ok=True)
    if not ROOKIE_FILTER.exists():
        shutil.copyfile(ROOKIE_FILTER_ORIGIN, ROOKIE_FILTER)
    first_seasons = fetch_first_seasons(refresh)
    return players, teams, playoff_players, playoff_teams, pd.read_csv(ROOKIE_FILTER), first_seasons


def render_boxed(ranked, final=True):
    """Draw the ranked games as bordered cards, reusing the Game Score by height grammar."""
    rows = len(ranked)
    fig_h = cards.figure_height(rows)
    fig, ax = plt.subplots(figsize=(cards.FIG_W, fig_h))
    fig.patch.set_alpha(0)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.set_axis_off()
    ax.patch.set_alpha(0)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.autoscale(False)
    theme = house.DEFAULT_THEME
    row_h = cards.ROW_H_IN / fig_h
    top = 1 - cards.PAD_TOP_IN / fig_h
    stripe_y = cards.STRIPE * cards.FIG_W / fig_h
    rank_right, portrait_x, name_x, score_left = 0.112, 0.168, 0.245, 0.895
    for i, (_, row) in enumerate(ranked.iterrows()):
        y = top - (i + 0.5) * row_h
        box_h = row_h * 0.86
        bottom = y - box_h / 2
        cards.striped_box(ax, cards.X_ROW_L, bottom, cards.X_ROW_R - cards.X_ROW_L, box_h,
                          cards.BULLS_RED, cards._mix('#FFFFFF', cards.BULLS_RED, 0.11), fig_h, zorder=2)
        ax.add_patch(Rectangle((cards.X_ROW_L + cards.STRIPE, bottom + stripe_y),
                               rank_right - cards.X_ROW_L - cards.STRIPE, box_h - 2 * stripe_y,
                               facecolor=cards.BULLS_RED, edgecolor='none', zorder=3))
        ax.text((cards.X_ROW_L + cards.STRIPE + rank_right) / 2, y, str(int(row['rank'])),
                fontproperties=house.helvetica('bold'), fontsize=26, color='white',
                ha='center', va='center', zorder=4)
        cards.place_portrait(ax, games.HEADSHOT_CACHE / f"{int(row.player_id)}.png", portrait_x,
                             bottom + cards.PORTRAIT_LIFT_IN / fig_h, row_h * cards.PORTRAIT_SCALE,
                             fig_h, 10 + i)
        ax.text(name_x, y + row_h * 0.12, games._display_name(row.player),
                fontproperties=house.helvetica('bold'), fontsize=19, color=theme.ink,
                ha='left', va='center', zorder=5)
        date = pd.Timestamp(row.game_date).strftime('%b %-d, %Y')
        site = 'vs' if 'vs.' in row.matchup else 'at'
        context_y = y - row_h * 0.18
        cursor = name_x
        note = str(row.get('context_note', '') or '')
        for text, size, weight, color in ((date, 12, None, theme.muted),
                                          (f'{site} {row.opponent}', 12, None, theme.muted),
                                          (note if note != 'nan' else '', 10.5, None, theme.muted),
                                          (row.result, 12, 'bold', '#3FAE63' if row.result == 'W' else '#D64545')):
            if not text:
                continue
            artist = ax.text(cursor, context_y, text, fontproperties=house.helvetica(weight) if weight else house.helvetica(),
                             fontsize=size, color=color, ha='left', va='center', zorder=5)
            cursor += house.rendered_width(ax, artist) + 0.006
        stat_specs = (('PTS', int(row.points), 0.040), ('FG', f'{int(row.fgm)}-{int(row.fga)}', 0.065),
                      ('REB', int(row.reb), 0.045), ('AST', int(row.ast), 0.040),
                      ('STL', int(row.stl), 0.040), ('BLK', int(row.blk), 0.040),
                      ('+/-', f'{int(row.plus_minus):+d}', 0.045))
        stat_cursor = 0.528
        for label, value, width in stat_specs:
            x = stat_cursor + width / 2
            stat_cursor += width + 0.0037
            ax.text(x, y + row_h * 0.105, str(value), ha='center', va='center', color=theme.ink,
                    fontsize=19, fontproperties=house.helvetica('bold'), zorder=5)
            ax.text(x, y - row_h * 0.105, label, ha='center', va='center', color=theme.muted,
                    fontsize=10, fontproperties=house.helvetica('bold'), zorder=5)
        fill = game_score_fill(row.game_score)
        cards.striped_box(ax, score_left, bottom, cards.X_ROW_R - score_left, box_h, fill, fill, fig_h, zorder=5)
        ax.text((score_left + cards.X_ROW_R) / 2, y, f'{row.game_score:.1f}',
                fontproperties=house.helvetica('bold'), fontsize=21.5, color='white',
                ha='center', va='center', zorder=7,
                path_effects=[cards.path_effects.withStroke(linewidth=3.5, foreground=house.BULLS_BLACK)])
    games.OUT.mkdir(exist_ok=True)
    path = games.OUT / f"rookie-game-scores-boxed-{'final' if final else 'draft'}.png"
    fig.savefig(path, dpi=400 if final else 200, transparent=True)
    plt.close(fig)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    players, teams, playoff_players, playoff_teams, rookie_filter, first_seasons = load_sources(args.refresh)
    table, reconciliation, rookie_audit, rookies, ranked = prepare(
        players, teams, playoff_players, playoff_teams, rookie_filter, first_seasons)
    bulls_ids = set(table.player_id)
    first_seasons.loc[first_seasons.PERSON_ID.isin(bulls_ids)].to_csv(FIRST_SEASONS, index=False)
    for name, frame in (('reconciliation', reconciliation), ('rookie-audit', rookie_audit),
                        ('rookie-games', rookies), ('top-fifteen', ranked)):
        frame.to_csv(DATA / f'{name}.csv', index=False)
    print(ranked[['rank', 'player', 'pool', 'game_date', 'opponent', 'result', 'game_score',
                  'points', 'reb', 'ast']].to_string(index=False), flush=True)
    snapshot = datetime.now(ZoneInfo('America/Chicago'))
    report = {'seasons': '2000-01 through 2025-26', 'season_type': 'Regular Season and Playoffs',
              'bulls_player_games': table.groupby('pool').size().to_dict(),
              'team_games': {'Regular season': len(teams), 'Playoffs': len(playoff_teams)},
              'playoff_seasons': sorted(PLAYOFF_SEASONS),
              'all_scores_reconciled': True, 'rookie_player_seasons': len(rookie_audit),
              'rookie_player_games': rookies.groupby('pool').size().to_dict(),
              'first_season_disagreements': sorted(map(list, KNOWN_FIRST_SEASON_DISAGREEMENTS)),
              'selected_games': TOP_N, 'cutoff': [float(rookies.game_score.nlargest(TOP_N).min()),
                                                 float(rookies.game_score.nlargest(TOP_N + 1).min())],
              'tiebreak': 'Game Score, then points', 'prepared_at': snapshot.isoformat(),
              'refreshed_this_run': args.refresh, 'rookie_source': str(ROOKIE_FILTER_ORIGIN.relative_to(ROOT)),
              'player_source': games.player_source_url(2026), 'team_source': games.team_source_url(2026)}
    (DATA / 'audit.json').write_text(json.dumps(report, indent=2) + '\n')
    (DATA / 'canva-copy.txt').write_text(
        'BEST BULLS ROOKIE GAMES\nTop 15 rookie performances since 2000–01\n'
        'Ranked by Hollinger Game Score\n'
        'Regular season and playoffs • Overtime included • Repeat players eligible • Ties broken by points\n'
        'Game Score measures box-score production. FG and 3PT show makes–attempts; TOV is turnovers.\n'
        'Source: NBA.com • Calculations: @chicagobullsdata\n')
    games.ensure_headshots(ranked.player_id.tolist())
    games.ensure_historical_headshot_fallbacks(ranked.player_id.tolist())
    use_post_portraits(ranked.player_id.tolist())
    print(games.render_chart(ranked, snapshot.date().isoformat(), decade=LABEL,
                             show_free_throws=False, show_turnovers=True, top_n=TOP_N,
                             layout=TABLE_LAYOUT, final=True, emphasize_points=True))


if __name__ == '__main__':
    main()
