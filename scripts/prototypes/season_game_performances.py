"""Top fifteen Bulls player-games in 2025–26 using the established Game Score table."""
from pathlib import Path
from dataclasses import replace
import argparse
import json
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
from scripts.prototypes import top_game_performances as games

DATA = ROOT / 'docs/visuals/2026-09-05-top-game-score-2025-26/data'


def prepare(players, teams):
    players, teams = players.copy(), teams.copy()
    for frame in (players, teams):
        frame['game_id'] = frame['game_id'].astype(str).str.zfill(10)
    table = games.build_working_table(players, teams)
    if set(table.season_end_year) != {2026} or len(teams) != 82:
        raise ValueError('Expected the complete 82-game 2025–26 regular season.')
    if set(table.game_id) != set(teams.game_id):
        raise ValueError('Player and team game coverage differs.')
    reconciliation = table.groupby('game_id', as_index=False).agg(
        player_points=('points', 'sum'), team_points=('team_points', 'first'))
    if not reconciliation.player_points.eq(reconciliation.team_points).all():
        raise ValueError('Player points do not reconcile to team scores.')
    if not np.isfinite(table[['game_score', 'ts_pct']]).all().all():
        raise ValueError('Nonfinite derived metric.')
    ranked = games.top_games_by_decade(table, top_n=15)
    if len(ranked) != 15:
        raise ValueError('Expected fifteen ranked player-games.')
    return players, teams, table, reconciliation, ranked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    frames = prepare(games.fetch_bulls_season(2026, refresh=args.refresh),
                     games.fetch_bulls_team_games(2026, refresh=args.refresh))
    DATA.mkdir(parents=True, exist_ok=True)
    for name, frame in zip(('players-source', 'teams-source', 'working', 'reconciliation', 'top-fifteen'), frames):
        frame.to_csv(DATA / f'{name}.csv', index=False)
    ranked = frames[-1]
    print(ranked[['rank','player','game_date','opponent','result','game_score','points','reb','ast','ts_pct']].to_string(index=False), flush=True)
    snapshot = datetime.now(ZoneInfo('America/Chicago'))
    report = {'season':'2025-26', 'season_type':'Regular Season', 'player_games':len(frames[2]),
              'team_games':len(frames[1]), 'all_scores_reconciled':True,
              'selected_games':15, 'source_refreshed_on':'2026-09-05', 'prepared_at':snapshot.isoformat(), 'refreshed_this_run':args.refresh,
              'player_source':games.player_source_url(2026), 'team_source':games.team_source_url(2026)}
    (DATA/'audit.json').write_text(json.dumps(report, indent=2)+'\n')
    (DATA/'canva-copy.txt').write_text(
        'THE BEST BULLS GAMES\nTop 15 individual performances of 2025–26\n'
        'Ranked by Hollinger Game Score\n'
        '2025–26 regular season • Repeat players eligible • Overtime included\n'
        'Game Score measures box-score production. FG, 3PT and FT show makes–attempts; TOV is turnovers.\n'
        'Source: NBA.com • Calculations: @chicagobullsdata\n')
    games.ensure_headshots(ranked.player_id.tolist())
    print(games.render_chart(ranked, snapshot.date().isoformat(), decade='2025-26',
                             show_free_throws=True, show_turnovers=True, top_n=15,
                             layout=replace(games.DECADE_LAYOUT, row_height=96, headshot_x=52,
                                            name_x=112, headshot_half_size=52, headshot_rise=4,
                                            first_row_from_top=145, bottom_pad=42),
                             final=True))


if __name__ == '__main__':
    main()
