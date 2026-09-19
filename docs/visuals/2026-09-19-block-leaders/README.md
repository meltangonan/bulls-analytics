# Bulls single-season block leaders

Top fifteen Bulls player-seasons by total blocks from 2000-01 through 2025-26.
The red bar carries blocks; support columns show that block total's NBA rank and
blocks per game. The window is an editorial era choice consistent with other
account posts, not an NBA.com coverage boundary.

Notion: https://www.notion.so/3e0e1c13abe6817185deeac5bababd36

## Build

```bash
python scripts/prototypes/block_leaders_data.py
python scripts/prototypes/block_leaders_table.py --final
```

Use `--refresh` on the data command to replace the saved NBA responses.

## Source and selection

NBA.com `LeagueDashPlayerStats`, regular season, totals. One team-filtered call
per season supplies Chicago-only totals; one unfiltered call supplies the full
league population. NBA rank is competition rank: tied totals share the same
rank. Matas Buzelis and Scottie Barnes both blocked 116 shots in 2025-26, so
both rank sixth.

Rows are ordered by blocks, then blocks per game, then the older season. The
secondary sort matters at the cutoff: Tyson Chandler 2005-06 and Taj Gibson
2009-10 both had 104 blocks, but Chandler's 1.32 per game exceeds Gibson's 1.27.
The graphic therefore stays at exactly fifteen rows without hiding its rule.

`data/bulls_player_seasons.csv` holds every Chicago player-season,
`data/top15.csv` is the displayed selection, `data/season_audit.csv` records
the row and block totals returned each season, and `data/selection_audit.csv`
confirms every displayed Chicago total equals that player's full-season total
and every calculated NBA rank matches NBA.com's rank. `data/source.json`
records the request contract and cutoff audit. Saved endpoint responses are
under `data/raw/`.

Blocks per game is shown instead of blocks per 75 possessions because the post
ranks a familiar counting stat. NBA rank supplies league context; a possession
rate would shift the story toward opportunity-adjusted shot blocking.

The 3:4 table asset uses a taller body ratio measured from the Canva draft.
`NBA RANK` wraps to two lines and `BLK/G` stays on one line, allowing a tighter
identity-to-bar gap and taller rows without shortening the blocks bar.

## Framing

This is a blocks leaderboard, not an overall rim-protection ranking. Matas's
strong block total should not be described as proof that he was an elite rim
protector; the separate rim-protection post measures that question directly.
