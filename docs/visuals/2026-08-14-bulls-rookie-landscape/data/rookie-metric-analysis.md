# Bulls rookie metric comparison

Regular-season Bulls rookie seasons from 2000-01 through 2025-26. NBA.com defines `Rookie` and supplies Bulls-stint totals and player possessions. Basketball Reference supplies TS%, Win Shares, BPM, and VORP.

## Population audit

- 76 player-seasons from 76 players
- 26 of 26 seasons contain at least one Bulls rookie
- Seasons with none: None
- 0+ minutes: 76 rookie seasons
- 300+ minutes: 46 rookie seasons
- 500+ minutes: 38 rookie seasons
- 750+ minutes: 32 rookie seasons
- 1,000+ minutes: 23 rookie seasons
- Without a floor, Max Strus's 6-minute stint ranks first in BPM and Adama Sanogo's 66-minute stint ranks first in PRA/75. A role or minutes dimension is mandatory for either rate statistic.

## What each measure rewards

- **BPM:** estimated box-score contribution per 100 possessions. Rate only; small samples can rank highly.
- **VORP:** BPM translated into estimated total value above replacement, so playing time is part of the result.
- **Win Shares:** estimated player contribution to team wins, split from offensive and defensive components. It is cumulative and team-influenced, so it fits the owner's win-context intuition without assigning the entire year-over-year team change to one rookie.
- **PPG:** scoring per appearance. Familiar, but rewards scoring only and is affected by minutes per game and pace.
- **PRA/75:** points + rebounds + assists per 75 player possessions. Adjusts for pace/opportunity, but does not measure efficiency or overall impact and weights unlike box-score events equally.

## Rank agreement (500+ minutes)

Spearman correlation compares ordering, not whether the metric values have the same units. A value near 1 means the two measures rank these rookies similarly.

| Measure | BPM | VORP | Win Shares | PPG | PRA/75 |
| --- | ---: | ---: | ---: | ---: | ---: |
| BPM | 1.00 | 0.98 | 0.84 | 0.49 | 0.47 |
| VORP | 0.98 | 1.00 | 0.79 | 0.41 | 0.46 |
| Win Shares | 0.84 | 0.79 | 1.00 | 0.54 | 0.51 |
| PPG | 0.49 | 0.41 | 0.54 | 1.00 | 0.62 |
| PRA/75 | 0.47 | 0.46 | 0.51 | 0.62 | 1.00 |

## Selected fan-facing table

The selected direction shows all 46 rookies with at least 300 Bulls regular-season minutes in chronological order. Columns are original overall draft pick or UDFA, GP, MPG, PTS, REB, AST, STL+BLK, TOV, TS%, Win Shares, and BPM. Square performance cells reuse the recent table family's red-yellow-green scale from each full-pool column minimum to maximum; opportunity and TOV remain plain. Color is not an overall ranking.

The earlier equal-weight composite remains in the tracked data as an exploratory sensitivity check, not the selected editorial framing.

## Derrick Rose and the Bulls' eight-win improvement

Chicago improved from 33-49 in 2007-08 to 41-41 in Rose's 2008-09 rookie season. That is valid team context, not a causal estimate of eight wins created by Rose. Rose recorded 4.9 Win Shares, second among the 1,000-minute rookies in this dataset, and 1.2 VORP despite a -0.4 BPM. His BPM combines +1.1 OBPM and -1.5 DBPM; the box-score defensive estimate is what pulls the rate slightly below league average.

## Discarded playstyle direction

A three-point-share versus restricted-area-share scatter was explored, but it answers a playstyle question rather than the owner's eventual best-rookie-season question. Its shot-zone inputs remain archived for audit and possible reuse, but they do not enter the composite or first table draft.

## Leaders with 500+ minutes

### BPM

| Rank | Rookie season | Minutes | BPM | VORP | WS | PPG | PRA/75 |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | Nikola Mirotic, 2014-15 | 1,654 | +2.3 | 1.8 | 5.7 | 10.2 | 30.7 |
| 2 | Luol Deng, 2004-05 | 1,661 | +1.2 | 1.3 | 3.0 | 11.7 | 26.7 |
| 3 | Ben Gordon, 2004-05 | 2,013 | +0.7 | 1.4 | 3.5 | 15.1 | 30.3 |
| 4 | Lauri Markkanen, 2017-18 | 2,020 | -0.2 | 0.9 | 3.3 | 15.2 | 29.0 |
| 5 | Joakim Noah, 2007-08 | 1,534 | -0.2 | 0.7 | 3.8 | 6.6 | 24.5 |
| 6 | Derrick Rose, 2008-09 | 3,000 | -0.4 | 1.2 | 4.9 | 16.8 | 27.8 |
| 7 | Chris Duhon, 2004-05 | 2,172 | -0.7 | 0.7 | 4.1 | 5.9 | 19.5 |
| 8 | Kirk Hinrich, 2003-04 | 2,709 | -0.8 | 0.8 | 4.1 | 12.0 | 24.2 |
| 9 | Tyrus Thomas, 2006-07 | 966 | -1.0 | 0.2 | 2.2 | 5.2 | 26.2 |
| 10 | Daniel Gafford, 2019-20 | 609 | -1.3 | 0.1 | 1.9 | 5.1 | 20.1 |

### VORP

| Rank | Rookie season | Minutes | BPM | VORP | WS | PPG | PRA/75 |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | Nikola Mirotic, 2014-15 | 1,654 | +2.3 | 1.8 | 5.7 | 10.2 | 30.7 |
| 2 | Ben Gordon, 2004-05 | 2,013 | +0.7 | 1.4 | 3.5 | 15.1 | 30.3 |
| 3 | Luol Deng, 2004-05 | 1,661 | +1.2 | 1.3 | 3.0 | 11.7 | 26.7 |
| 4 | Derrick Rose, 2008-09 | 3,000 | -0.4 | 1.2 | 4.9 | 16.8 | 27.8 |
| 5 | Lauri Markkanen, 2017-18 | 2,020 | -0.2 | 0.9 | 3.3 | 15.2 | 29.0 |
| 6 | Kirk Hinrich, 2003-04 | 2,709 | -0.8 | 0.8 | 4.1 | 12.0 | 24.2 |
| 7 | Chris Duhon, 2004-05 | 2,172 | -0.7 | 0.7 | 4.1 | 5.9 | 19.5 |
| 8 | Joakim Noah, 2007-08 | 1,534 | -0.2 | 0.7 | 3.8 | 6.6 | 24.5 |
| 9 | Tyrus Thomas, 2006-07 | 966 | -1.0 | 0.2 | 2.2 | 5.2 | 26.2 |
| 10 | Wendell Carter Jr., 2018-19 | 1,110 | -1.6 | 0.1 | 1.9 | 10.3 | 27.6 |

### Win Shares

| Rank | Rookie season | Minutes | BPM | VORP | WS | PPG | PRA/75 |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | Nikola Mirotic, 2014-15 | 1,654 | +2.3 | 1.8 | 5.7 | 10.2 | 30.7 |
| 2 | Derrick Rose, 2008-09 | 3,000 | -0.4 | 1.2 | 4.9 | 16.8 | 27.8 |
| 3 | Taj Gibson, 2009-10 | 2,204 | -2.0 | 0.0 | 4.7 | 9.0 | 24.7 |
| 4 | Kirk Hinrich, 2003-04 | 2,709 | -0.8 | 0.8 | 4.1 | 12.0 | 24.2 |
| 5 | Chris Duhon, 2004-05 | 2,172 | -0.7 | 0.7 | 4.1 | 5.9 | 19.5 |
| 6 | Joakim Noah, 2007-08 | 1,534 | -0.2 | 0.7 | 3.8 | 6.6 | 24.5 |
| 7 | Ben Gordon, 2004-05 | 2,013 | +0.7 | 1.4 | 3.5 | 15.1 | 30.3 |
| 8 | Lauri Markkanen, 2017-18 | 2,020 | -0.2 | 0.9 | 3.3 | 15.2 | 29.0 |
| 9 | Ayo Dosunmu, 2021-22 | 2,110 | -2.0 | 0.0 | 3.0 | 8.8 | 19.5 |
| 10 | Luol Deng, 2004-05 | 1,661 | +1.2 | 1.3 | 3.0 | 11.7 | 26.7 |

### PPG

| Rank | Rookie season | Minutes | BPM | VORP | WS | PPG | PRA/75 |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | Derrick Rose, 2008-09 | 3,000 | -0.4 | 1.2 | 4.9 | 16.8 | 27.8 |
| 2 | Lauri Markkanen, 2017-18 | 2,020 | -0.2 | 0.9 | 3.3 | 15.2 | 29.0 |
| 3 | Ben Gordon, 2004-05 | 2,013 | +0.7 | 1.4 | 3.5 | 15.1 | 30.3 |
| 4 | Coby White, 2019-20 | 1,674 | -2.9 | -0.4 | 0.9 | 13.2 | 26.5 |
| 5 | Kirk Hinrich, 2003-04 | 2,709 | -0.8 | 0.8 | 4.1 | 12.0 | 24.2 |
| 6 | Luol Deng, 2004-05 | 1,661 | +1.2 | 1.3 | 3.0 | 11.7 | 26.7 |
| 7 | Wendell Carter Jr., 2018-19 | 1,110 | -1.6 | 0.1 | 1.9 | 10.3 | 27.6 |
| 8 | Nikola Mirotic, 2014-15 | 1,654 | +2.3 | 1.8 | 5.7 | 10.2 | 30.7 |
| 9 | Jay Williams, 2002-03 | 1,961 | -2.0 | 0.0 | 0.8 | 9.5 | 23.9 |
| 10 | Marcus Fizer, 2000-01 | 1,581 | -6.1 | -1.6 | -0.7 | 9.5 | 26.5 |

### PRA per 75 possessions

| Rank | Rookie season | Minutes | BPM | VORP | WS | PPG | PRA/75 |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | Nikola Mirotic, 2014-15 | 1,654 | +2.3 | 1.8 | 5.7 | 10.2 | 30.7 |
| 2 | Ben Gordon, 2004-05 | 2,013 | +0.7 | 1.4 | 3.5 | 15.1 | 30.3 |
| 3 | Lauri Markkanen, 2017-18 | 2,020 | -0.2 | 0.9 | 3.3 | 15.2 | 29.0 |
| 4 | Aaron Gray, 2007-08 | 613 | -3.5 | -0.2 | 0.8 | 4.3 | 28.9 |
| 5 | Derrick Rose, 2008-09 | 3,000 | -0.4 | 1.2 | 4.9 | 16.8 | 27.8 |
| 6 | Bobby Portis Jr., 2015-16 | 1,102 | -3.3 | -0.4 | 1.5 | 7.0 | 27.7 |
| 7 | Wendell Carter Jr., 2018-19 | 1,110 | -1.6 | 0.1 | 1.9 | 10.3 | 27.6 |
| 8 | Luol Deng, 2004-05 | 1,661 | +1.2 | 1.3 | 3.0 | 11.7 | 26.7 |
| 9 | Coby White, 2019-20 | 1,674 | -2.9 | -0.4 | 0.9 | 13.2 | 26.5 |
| 10 | Marcus Fizer, 2000-01 | 1,581 | -6.1 | -1.6 | -0.7 | 9.5 | 26.5 |

## Leaders with 1,000+ minutes

### BPM

| Rank | Rookie season | Minutes | BPM | VORP | WS | PPG | PRA/75 |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | Nikola Mirotic, 2014-15 | 1,654 | +2.3 | 1.8 | 5.7 | 10.2 | 30.7 |
| 2 | Luol Deng, 2004-05 | 1,661 | +1.2 | 1.3 | 3.0 | 11.7 | 26.7 |
| 3 | Ben Gordon, 2004-05 | 2,013 | +0.7 | 1.4 | 3.5 | 15.1 | 30.3 |
| 4 | Lauri Markkanen, 2017-18 | 2,020 | -0.2 | 0.9 | 3.3 | 15.2 | 29.0 |
| 5 | Joakim Noah, 2007-08 | 1,534 | -0.2 | 0.7 | 3.8 | 6.6 | 24.5 |
| 6 | Derrick Rose, 2008-09 | 3,000 | -0.4 | 1.2 | 4.9 | 16.8 | 27.8 |
| 7 | Chris Duhon, 2004-05 | 2,172 | -0.7 | 0.7 | 4.1 | 5.9 | 19.5 |
| 8 | Kirk Hinrich, 2003-04 | 2,709 | -0.8 | 0.8 | 4.1 | 12.0 | 24.2 |
| 9 | Wendell Carter Jr., 2018-19 | 1,110 | -1.6 | 0.1 | 1.9 | 10.3 | 27.6 |
| 10 | Taj Gibson, 2009-10 | 2,204 | -2.0 | 0.0 | 4.7 | 9.0 | 24.7 |

### VORP

| Rank | Rookie season | Minutes | BPM | VORP | WS | PPG | PRA/75 |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | Nikola Mirotic, 2014-15 | 1,654 | +2.3 | 1.8 | 5.7 | 10.2 | 30.7 |
| 2 | Ben Gordon, 2004-05 | 2,013 | +0.7 | 1.4 | 3.5 | 15.1 | 30.3 |
| 3 | Luol Deng, 2004-05 | 1,661 | +1.2 | 1.3 | 3.0 | 11.7 | 26.7 |
| 4 | Derrick Rose, 2008-09 | 3,000 | -0.4 | 1.2 | 4.9 | 16.8 | 27.8 |
| 5 | Lauri Markkanen, 2017-18 | 2,020 | -0.2 | 0.9 | 3.3 | 15.2 | 29.0 |
| 6 | Kirk Hinrich, 2003-04 | 2,709 | -0.8 | 0.8 | 4.1 | 12.0 | 24.2 |
| 7 | Chris Duhon, 2004-05 | 2,172 | -0.7 | 0.7 | 4.1 | 5.9 | 19.5 |
| 8 | Joakim Noah, 2007-08 | 1,534 | -0.2 | 0.7 | 3.8 | 6.6 | 24.5 |
| 9 | Wendell Carter Jr., 2018-19 | 1,110 | -1.6 | 0.1 | 1.9 | 10.3 | 27.6 |
| 10 | Taj Gibson, 2009-10 | 2,204 | -2.0 | 0.0 | 4.7 | 9.0 | 24.7 |

### Win Shares

| Rank | Rookie season | Minutes | BPM | VORP | WS | PPG | PRA/75 |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | Nikola Mirotic, 2014-15 | 1,654 | +2.3 | 1.8 | 5.7 | 10.2 | 30.7 |
| 2 | Derrick Rose, 2008-09 | 3,000 | -0.4 | 1.2 | 4.9 | 16.8 | 27.8 |
| 3 | Taj Gibson, 2009-10 | 2,204 | -2.0 | 0.0 | 4.7 | 9.0 | 24.7 |
| 4 | Kirk Hinrich, 2003-04 | 2,709 | -0.8 | 0.8 | 4.1 | 12.0 | 24.2 |
| 5 | Chris Duhon, 2004-05 | 2,172 | -0.7 | 0.7 | 4.1 | 5.9 | 19.5 |
| 6 | Joakim Noah, 2007-08 | 1,534 | -0.2 | 0.7 | 3.8 | 6.6 | 24.5 |
| 7 | Ben Gordon, 2004-05 | 2,013 | +0.7 | 1.4 | 3.5 | 15.1 | 30.3 |
| 8 | Lauri Markkanen, 2017-18 | 2,020 | -0.2 | 0.9 | 3.3 | 15.2 | 29.0 |
| 9 | Ayo Dosunmu, 2021-22 | 2,110 | -2.0 | 0.0 | 3.0 | 8.8 | 19.5 |
| 10 | Luol Deng, 2004-05 | 1,661 | +1.2 | 1.3 | 3.0 | 11.7 | 26.7 |

### PPG

| Rank | Rookie season | Minutes | BPM | VORP | WS | PPG | PRA/75 |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | Derrick Rose, 2008-09 | 3,000 | -0.4 | 1.2 | 4.9 | 16.8 | 27.8 |
| 2 | Lauri Markkanen, 2017-18 | 2,020 | -0.2 | 0.9 | 3.3 | 15.2 | 29.0 |
| 3 | Ben Gordon, 2004-05 | 2,013 | +0.7 | 1.4 | 3.5 | 15.1 | 30.3 |
| 4 | Coby White, 2019-20 | 1,674 | -2.9 | -0.4 | 0.9 | 13.2 | 26.5 |
| 5 | Kirk Hinrich, 2003-04 | 2,709 | -0.8 | 0.8 | 4.1 | 12.0 | 24.2 |
| 6 | Luol Deng, 2004-05 | 1,661 | +1.2 | 1.3 | 3.0 | 11.7 | 26.7 |
| 7 | Wendell Carter Jr., 2018-19 | 1,110 | -1.6 | 0.1 | 1.9 | 10.3 | 27.6 |
| 8 | Nikola Mirotic, 2014-15 | 1,654 | +2.3 | 1.8 | 5.7 | 10.2 | 30.7 |
| 9 | Jay Williams, 2002-03 | 1,961 | -2.0 | 0.0 | 0.8 | 9.5 | 23.9 |
| 10 | Marcus Fizer, 2000-01 | 1,581 | -6.1 | -1.6 | -0.7 | 9.5 | 26.5 |

### PRA per 75 possessions

| Rank | Rookie season | Minutes | BPM | VORP | WS | PPG | PRA/75 |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | Nikola Mirotic, 2014-15 | 1,654 | +2.3 | 1.8 | 5.7 | 10.2 | 30.7 |
| 2 | Ben Gordon, 2004-05 | 2,013 | +0.7 | 1.4 | 3.5 | 15.1 | 30.3 |
| 3 | Lauri Markkanen, 2017-18 | 2,020 | -0.2 | 0.9 | 3.3 | 15.2 | 29.0 |
| 4 | Derrick Rose, 2008-09 | 3,000 | -0.4 | 1.2 | 4.9 | 16.8 | 27.8 |
| 5 | Bobby Portis Jr., 2015-16 | 1,102 | -3.3 | -0.4 | 1.5 | 7.0 | 27.7 |
| 6 | Wendell Carter Jr., 2018-19 | 1,110 | -1.6 | 0.1 | 1.9 | 10.3 | 27.6 |
| 7 | Luol Deng, 2004-05 | 1,661 | +1.2 | 1.3 | 3.0 | 11.7 | 26.7 |
| 8 | Coby White, 2019-20 | 1,674 | -2.9 | -0.4 | 0.9 | 13.2 | 26.5 |
| 9 | Marcus Fizer, 2000-01 | 1,581 | -6.1 | -1.6 | -0.7 | 9.5 | 26.5 |
| 10 | Eddy Curry, 2001-02 | 1,151 | -4.4 | -0.7 | 1.8 | 6.7 | 26.1 |
