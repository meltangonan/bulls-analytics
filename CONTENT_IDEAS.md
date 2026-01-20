# Bulls Instagram Content Ideas

Reference document for creating Instagram content around Bulls stats and analysis.

---

## Current Data Capabilities

**What's available now:**
- Game logs, box scores, player game-by-game stats
- Shot chart data (location, zone, distance, made/missed)
- League-wide shot data for all 30 teams
- Points Per Shot (PPS) analysis by zone
- Shot selection quality metrics

**Key findings from existing analysis:**
- Bulls rank #1 in shot selection (78.7% high-value shots)
- Bulls rank #28 at the rim (Restricted Area efficiency)
- Bulls rank #4 in right corner 3 efficiency (90th percentile)
- Bulls are -91 points vs league-average execution this season

---

## Content Ideas

### Tier 1: Unique Narratives

#### "The Bulls Paradox"
Bulls are #1 in shot selection but #28 at the rim. Visualize the disconnect between shooting from the right spots vs making those shots.

#### "The Right Corner Snipers"
Bulls are #4 in the league from right corner 3. Corner-3 specific leaderboard with headshots and percentages.

#### "28th at the Rim"
Shot chart of all rim attempts highlighting the miss rate. Compare to league leaders.

#### "Shot Diet" Player Profiles
Each player's shot zone distribution as pie/donut chart. Julian Phillips: 95.9% high-value. Vučević: 57.3%.

#### "The Execution Gap"
"If Bulls shot league average from each zone, they'd have X more wins."

---

### Tier 2: Weekly/Game Recaps

#### "Heat Check" - Post-Game Shot Charts
After every game, post the Bulls shot chart with makes/misses. Highlight the hot player.

#### "Zone of the Night"
After big performances, show where a player scored from with shots highlighted on court.

#### "Efficiency Report Card"
Weekly visual showing each starter's PPS with letter grades based on league percentiles.

---

### Tier 3: Player Spotlights

#### "The Giddey Zone"
Josh Giddey leads restricted area at 6.28 PPG. Finishing at the rim analysis.

#### "Matas Buzelis: Corner Specialist?"
Young player leading left corner 3s. Shot selection developmental story.

#### "Coby White's Shooting Gravity"
Shot chart density - where does he pull up from most? What zones does he own?

---

### Tier 4: League Context

#### "Bulls vs the League" Heatmaps
30-team efficiency heatmap with Bulls highlighted showing excel (green) vs struggle (red).

#### "Zone Wars"
Weekly ranking of all 30 teams by specific zone efficiency. Bulls highlighted.

---

## Additional Content Concepts

### "Winner by Bucket"
Leading scorer in each court zone. Similar to zone leaders but framed as "who wins each battle."

### "Volume vs Efficiency"
Scatter plot format - e.g., clutch points vs clutch TS%. Shows who performs under pressure vs who just takes shots.

### "Usage + Results"
Multi-metric breakdown - e.g., isolation possessions + PPP + FT% + TOV%. Who earns their usage?

### "Team Identity Map"
Scatter of all 30 teams: 3PA share vs rim share. Where do Bulls fall? Are they a modern offense or stuck in between?

### "Historical Context / Rarity"
Best point differentials through N games. "Only 5 teams in history have been +X through 40 games." Context for current performance.

---

## Data to Consider Adding

### High Priority

| Data Type | Content It Enables |
|-----------|-------------------|
| **Clutch data** | Shots in final 2 min of close games. "Clutch Shot Charts" |
| **Game result splits** | Shot selection in wins vs losses |
| **Opponent-specific** | Shot charts vs specific teams/defenses |
| **Rolling form** | Last 5 games hot zones vs season average |
| **Play type data** | Isolation, P&R, spot-up efficiency (NBA API has this) |
| **Assisted vs unassisted** | Who creates vs who needs setup |

### Lower Priority

- Home vs Away splits
- Quarter-by-quarter efficiency
- Back-to-back game performance
- Historical season comparisons

---

## Visual Style Notes

**What works on Instagram (kirkgoldsberry, datakabas, bballuniversity style):**

1. **Bold, clean typography** - Big numbers, minimal text
2. **Team colors as accent** - Bulls red sparingly, not overwhelming
3. **One insight per post** - Don't cram multiple charts
4. **Context in caption** - Visual hooks, caption explains
5. **Consistent template** - Recognizable brand across posts

**Adjustments from current viz style:**
- Larger fonts for mobile viewing
- Fewer grid lines
- More whitespace
- Logo/watermark branding
- Square format (1080x1080) or 4:5 ratio

---

## Implementation Priority

**Quick wins (current data):**
1. Zone Leaders / Winner by Bucket
2. Post-game shot charts
3. Team identity map (3PA vs rim share)
4. Bulls vs League heatmap

**Requires new data:**
1. Clutch analysis
2. Play type breakdowns
3. Historical comparisons
