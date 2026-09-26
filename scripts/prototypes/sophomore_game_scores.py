"""Top fifteen Bulls sophomore games since 1983–84 by Game Score, regular season and playoffs.

The sibling of the 2026-09-18 rookie post, with its pools, tiebreak and table, over the longest
window NBA.com's box scores support. A sophomore season is a player's second NBA regular season
with an appearance, read from NBA.com career histories. That is the rule behind NBA.com's own
Sophomore filter, which exists from 1996–97 and must agree with it for every season it covers;
CommonAllPlayers' first season is a second audit. A sophomore's playoff games that season share
the pool, and repeat players are eligible. Plus/minus is untracked before 1996–97, so the table
drops it, as the 1983–84 season-opener table does.
"""
from pathlib import Path
from dataclasses import replace
import argparse
import json
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from nba_api.stats.endpoints import commonallplayers, leaguedashplayerstats

from bulls.config import BULLS_TEAM_ID
from bulls.data.fetch import _NBA_HEADERS
from bulls.graphics.house import cut_out_flat_background
from scripts.prototypes import top_game_performances as games

DATA = ROOT / 'docs/visuals/2026-09-20-sophomore-game-scores/data'
SOPHOMORE_FILTER = DATA / 'nba-sophomore-filter-since-1996-97.csv'
FIRST_SEASONS = DATA / 'nba-common-all-players-first-seasons.csv'
CAREERS = DATA / 'career-seasons.csv'
SEASONS = range(1984, 2027)
FILTER_SEASONS = range(1997, 2027)  # LeagueDashPlayerStats has no season data before 1996–97
LABEL = 'Sophomores since 1983–84'
TOP_N = 15
# Taller rows than the 2025–26 table: the Canva page has room below the table at its width.
# Name, game line and cells run one point larger than the rookie table (user request, 2026-09-26).
TABLE_LAYOUT = replace(games.DECADE_LAYOUT, row_height=108, headshot_x=60, name_x=128,
                       headshot_half_size=66, headshot_rise=8, first_row_from_top=145,
                       bottom_pad=42, name_font_size=22, context_font_size=13.5,
                       value_font_size=17, gmsc_font_size=17, name_rise=16, context_drop=22)
# The NBA CDN serves a silhouette for Quintin Dailey. The user supplied a cropped portrait on flat
# white (2026-09-26); data/portraits_source keeps it unchanged.
PORTRAIT_SOURCES = {76497: 'Quintin Dailey.png'}
PLAYOFF_SEASONS = set(range(1985, 1999)) | {2005, 2006, 2007, 2009, 2010, 2011, 2012, 2013,
                                            2014, 2015, 2017, 2022}
# NBA.com's career endpoint returns an error body for these Bulls players (retried 2026-09-26).
# Their regular seasons played (end years) come from PlayerGameLogs(player_id_nullable=...) for
# each season in their CommonAllPlayers span, checked the same day.
CAREER_GAP_SEASONS = {
    1099: (1997,),        # Matt Steigenga: CHI 1996-97 only
    2000: (2000,),        # Dedric Willoughby: CHI 1999-00 only
    2839: (2005, 2006),   # James Thomas: ATL/POR 2004-05, CHI/PHI 2005-06 (a Bulls sophomore)
    200603: (1993, 1994), # Corey Williams: CHI 1992-93 (rookie), MIN 1993-94
}
# NBA.com credits these Bulls points to a nameless 0-minute row in both PlayerGameLogs and
# BoxScoreTraditionalV2. Team totals minus the named players leave only shooting for it, so its
# Game Score is at most 6.6, 4.3 and 1.3, far below any top-fifteen cutoff.
UNATTRIBUTED_POINTS = {'0028300217': 11, '0028300521': 7, '0028400293': 3}
# NBA.com leaves Game Score inputs blank for these regular-season rows: every Bulls player on
# 1983-11-23 (no rebound split or turnovers) and one player in each other game. Each value is the
# highest Game Score the row could have, crediting every rebound as offensive, no turnovers or
# fouls, and team totals minus the named players for anything else blank.
INCOMPLETE_BOX_SCORES = {'0028300147': 20.1, '0028400171': 3.4, '0028400234': 1.0,
                         '0028400278': 3.4, '0028400305': 4.7, '0028600427': 0.0}
# NBA.com's Sophomore filter labels Chris Anstey's 1999-00 Bulls season his sophomore year, but
# his career history shows DAL 1997-98 and 1998-99 first, so it was his third season played.
KNOWN_FILTER_DISAGREEMENTS = {(2000, 1512)}
# CommonAllPlayers' FROM_YEAR is the first season on a roster, so FROM_YEAR + 2 misses anyone who
# sat out a full season before their second one: Anthony Jones (WAS/SAS 1986-87, out 1987-88),
# Chris Richard (MIN 2007-08, out 2008-09), E.J. Liddell (drafted 2022, first played 2023-24)
# and Mouhamadou Gueye (TOR 2023-24, out 2024-25). Second season played decides.
KNOWN_FIRST_SEASON_DISAGREEMENTS = {(1989, 77173), (2010, 201181), (2025, 1630604), (2026, 1631338)}


def fetch_sophomore_filter(refresh=False):
    """Load NBA.com's Sophomore experience filter for each Bulls season it covers."""
    if SOPHOMORE_FILTER.exists() and not refresh:
        return pd.read_csv(SOPHOMORE_FILTER)
    rows = []
    for end_year in FILTER_SEASONS:
        label = f'{end_year - 1}-{str(end_year)[2:]}'
        frame = leaguedashplayerstats.LeagueDashPlayerStats(
            team_id_nullable=BULLS_TEAM_ID, season=label, season_type_all_star='Regular Season',
            player_experience_nullable='Sophomore', per_mode_detailed='Totals',
            measure_type_detailed_defense='Base', timeout=60,
            headers=_NBA_HEADERS).get_data_frames()[0]
        for _, player in frame.iterrows():
            rows.append({'season': end_year, 'season_label': label,
                         'player_id': int(player.PLAYER_ID), 'player_name': player.PLAYER_NAME,
                         'games': int(player.GP)})
        time.sleep(0.7)
    return pd.DataFrame(rows)


def fetch_first_seasons(refresh=False):
    """Load NBA.com's CommonAllPlayers first-season field, fetching once when absent."""
    if FIRST_SEASONS.exists() and not refresh:
        return pd.read_csv(FIRST_SEASONS)
    frame = commonallplayers.CommonAllPlayers(
        is_only_current_season=0, headers=_NBA_HEADERS, timeout=60).get_data_frames()[0]
    return frame[['PERSON_ID', 'DISPLAY_FIRST_LAST', 'FROM_YEAR', 'TO_YEAR']]


def post_portraits():
    """Cut the supplied portraits out of their white surround, framed like NBA headshots."""
    return {player_id: cut_out_flat_background(DATA / 'portraits_source' / name,
                                                DATA / 'portraits' / f'{player_id}.png')
            for player_id, name in PORTRAIT_SOURCES.items()}


def second_seasons_played(careers):
    """Map each player to the end year of their second NBA regular season with a game played.

    Career histories list a traded player once per team plus a TOT row, so seasons are counted
    once each. A player with a single season has no sophomore year.
    """
    played = careers.loc[careers.LEAGUE_ID.astype(int).eq(0) & careers.GP.gt(0)]
    seasons = played.groupby('PLAYER_ID').SEASON_ID.apply(lambda s: sorted(set(s)))
    second = {int(player): int(ids[1][:4]) + 1 for player, ids in seasons.items() if len(ids) > 1}
    second.update({player: years[1] for player, years in CAREER_GAP_SEASONS.items() if len(years) > 1})
    return second


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
    reconciliation['unattributed_points'] = reconciliation.game_id.map(UNATTRIBUTED_POINTS).fillna(0).astype(int)
    if not (reconciliation.player_points + reconciliation.unattributed_points).eq(
            reconciliation.team_points).all():
        raise ValueError(f'{pool} player points do not reconcile to team scores.')
    blank = ~np.isfinite(table.game_score)
    if set(table.loc[blank, 'game_id']) != (set(INCOMPLETE_BOX_SCORES) if pool == 'Regular season' else set()):
        raise ValueError(f'{pool} has undocumented blank Game Score inputs.')
    table['pool'] = reconciliation['pool'] = pool
    table['context_note'] = table.game_id.map(playoff_context) if pool == 'Playoffs' else ''
    return table, reconciliation


def prepare(players, teams, playoff_players, playoff_teams, sophomore_filter, first_seasons,
            careers):
    table, reconciliation = validated_pool(players, teams, 'Regular season', SEASONS)
    playoffs, playoff_reconciliation = validated_pool(
        playoff_players, playoff_teams, 'Playoffs', PLAYOFF_SEASONS)

    played = set(zip(table.season_end_year, table.player_id))
    bulls_ids = {p for _, p in played}
    if bulls_ids - set(CAREER_GAP_SEASONS) != bulls_ids & set(careers.PLAYER_ID.astype(int)):
        raise ValueError('A Bulls player is missing a career history.')
    spans = first_seasons.set_index('PERSON_ID')
    for player, years in CAREER_GAP_SEASONS.items():
        if (int(spans.FROM_YEAR[player]) + 1, int(spans.TO_YEAR[player]) + 1) != (years[0], years[-1]):
            raise ValueError(f'Hand-checked seasons for {player} disagree with CommonAllPlayers.')
    second = second_seasons_played(careers)
    pairs = {(y, p) for y, p in played if second.get(p) == y}

    # NBA.com's own label must match the rule wherever NBA.com has one.
    nba_pairs = set(zip(sophomore_filter.season.astype(int), sophomore_filter.player_id.astype(int)))
    in_filter_years = {(y, p) for y, p in pairs if y in FILTER_SEASONS}
    if nba_pairs ^ in_filter_years != KNOWN_FILTER_DISAGREEMENTS:
        raise ValueError(f'Second season played disagrees with NBA.com: '
                         f'{sorted(nba_pairs ^ in_filter_years)}.')

    first = first_seasons.set_index('PERSON_ID').FROM_YEAR
    if not bulls_ids <= set(first.index):
        raise ValueError('A Bulls player is missing from CommonAllPlayers.')
    by_first_season = {(y, p) for y, p in played if int(first[p]) == y - 2}
    if pairs ^ by_first_season != KNOWN_FIRST_SEASON_DISAGREEMENTS:
        raise ValueError(f'First-season audit disagrees: {sorted(pairs ^ by_first_season)}.')

    names = table.drop_duplicates('player_id').set_index('player_id').player
    season_games = table.groupby(['season_end_year', 'player_id']).size()
    filter_games = sophomore_filter.set_index(['season', 'player_id']).games
    audit = pd.DataFrame(sorted(pairs | by_first_season | nba_pairs), columns=['season', 'player_id'])
    audit['player_name'] = audit.player_id.map(names)
    audit['bulls_game_rows'] = [season_games.get((s, p), 0) for s, p in zip(audit.season, audit.player_id)]
    audit['second_season_played'] = [(s, p) in pairs for s, p in zip(audit.season, audit.player_id)]
    audit['nba_sophomore_filter'] = [
        ((s, p) in nba_pairs) if s in FILTER_SEASONS else pd.NA
        for s, p in zip(audit.season, audit.player_id)]
    audit['nba_filter_games'] = [filter_games.get((s, p), pd.NA) for s, p in zip(audit.season, audit.player_id)]
    audit['common_all_players_from_year'] = audit.player_id.map(first)
    audit['first_season_agrees'] = [
        ((s, p) in by_first_season) == ((s, p) in pairs) for s, p in zip(audit.season, audit.player_id)]
    checked = audit.nba_filter_games.notna()
    if not audit.loc[checked, 'nba_filter_games'].astype(int).eq(audit.loc[checked, 'bulls_game_rows']).all():
        raise ValueError('Sophomore filter games do not match Bulls game-log rows.')

    # Sophomore status is a regular-season fact; that season's playoff games inherit it.
    pool = pd.concat([table, playoffs], ignore_index=True)
    # The documented incomplete games also under-log minutes, so their period count stays unknown.
    documented = set(INCOMPLETE_BOX_SCORES) | set(UNATTRIBUTED_POINTS)
    periods = games.minute_reconciliation(pool.loc[~pool.game_id.isin(documented)]).overtime_periods
    pool['overtime_periods'] = pool.game_id.map(periods).astype('Int64')
    is_sophomore = np.array([pair in pairs for pair in zip(pool.season_end_year, pool.player_id)])
    sophomores = pool.loc[is_sophomore & np.isfinite(pool.game_score)].copy()
    reconciliation = pd.concat([reconciliation, playoff_reconciliation], ignore_index=True)
    ranked = select_top(sophomores)
    if ranked.overtime_periods.isna().any() or max(INCOMPLETE_BOX_SCORES.values()) >= ranked.game_score.min():
        raise ValueError('An incomplete box score could reach the top fifteen.')
    return pool, reconciliation, audit, sophomores, ranked


def select_top(sophomores, top_n=TOP_N):
    """Rank sophomore games by Game Score, then points, refusing a tie across the cutoff."""
    sophomores = sophomores.copy()
    # Every Game Score term is a multiple of 0.1; rounding strips float noise so an exact tie
    # falls through to the shared points tiebreak instead of an arbitrary 1e-15 difference.
    sophomores['game_score'] = sophomores.game_score.round(1)
    sophomores['decade'] = LABEL
    ranked = games.top_games_by_decade(sophomores, top_n=top_n + 1)
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
    careers = games.fetch_career_seasons(
        sorted(set(players.player_id.astype(int)) - set(CAREER_GAP_SEASONS)), CAREERS, refresh)
    return (players, teams, playoff_players, playoff_teams,
            fetch_sophomore_filter(refresh), fetch_first_seasons(refresh), careers)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    players, teams, playoff_players, playoff_teams, sophomore_filter, first_seasons, careers = (
        load_sources(args.refresh))
    table, reconciliation, audit, sophomores, ranked = prepare(
        players, teams, playoff_players, playoff_teams, sophomore_filter, first_seasons, careers)
    bulls_ids = set(table.player_id)
    sophomore_filter.to_csv(SOPHOMORE_FILTER, index=False)
    first_seasons.loc[first_seasons.PERSON_ID.isin(bulls_ids)].to_csv(FIRST_SEASONS, index=False)
    for name, frame in (('reconciliation', reconciliation), ('sophomore-audit', audit),
                        ('sophomore-games', sophomores), ('top-fifteen', ranked)):
        frame.to_csv(DATA / f'{name}.csv', index=False)
    print(ranked[['rank', 'player', 'pool', 'game_date', 'opponent', 'result', 'game_score',
                  'points', 'reb', 'ast']].to_string(index=False), flush=True)
    snapshot = datetime.now(ZoneInfo('America/Chicago'))
    report = {'seasons': '1983-84 through 2025-26', 'season_type': 'Regular Season and Playoffs',
              'bulls_player_games': table.groupby('pool').size().to_dict(),
              'team_games': {'Regular season': len(teams), 'Playoffs': len(playoff_teams)},
              'playoff_seasons': sorted(PLAYOFF_SEASONS),
              'all_scores_reconciled': True,
              'sophomore_player_seasons': int(audit.second_season_played.sum()),
              'sophomore_player_games': sophomores.groupby('pool').size().to_dict(),
              'sophomore_rule': 'second NBA regular season with a game played (PlayerCareerStats)',
              'nba_filter_agrees': f'every season {FILTER_SEASONS.start - 1}-{str(FILTER_SEASONS.start)[2:]} on',
              'first_season_disagreements': sorted(map(list, KNOWN_FIRST_SEASON_DISAGREEMENTS)),
              'selected_games': TOP_N,
              'cutoff': [float(sophomores.game_score.round(1).nlargest(TOP_N).min()),
                         float(sophomores.game_score.round(1).nlargest(TOP_N + 1).min())],
              'tiebreak': 'Game Score, then points', 'plus_minus': 'dropped; untracked before 1996-97',
              'prepared_at': snapshot.isoformat(), 'refreshed_this_run': args.refresh,
              'player_source': games.player_source_url(2026), 'team_source': games.team_source_url(2026)}
    (DATA / 'audit.json').write_text(json.dumps(report, indent=2) + '\n')
    (DATA / 'canva-copy.txt').write_text(
        "Bulls' best sophomore performances\n"
        'Top 15 in Hollinger Game Score by a sophomore, since 1983-84\n'
        'Data via NBA.com | 1983-84 to 2025-26 regular season and playoffs\n'
        'Sophomore: second NBA season with a game played • Overtime included • Ties broken by points\n')
    games.ensure_headshots(ranked.player_id.tolist())
    games.ensure_historical_headshot_fallbacks(ranked.player_id.tolist())
    print(games.render_chart(ranked, snapshot.date().isoformat(), decade=LABEL,
                             show_free_throws=False, show_turnovers=True, top_n=TOP_N,
                             layout=TABLE_LAYOUT, final=True, emphasize_points=True,
                             shooting_after_assists=True, show_plus_minus=False,
                             portraits=post_portraits()))


if __name__ == '__main__':
    main()
