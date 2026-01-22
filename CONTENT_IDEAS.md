# Bulls Instagram Content Ideas

Reference document for creating Instagram content around Bulls stats and analysis.

---

## The Formula: Visual + Callouts

Every post has:
1. **A visual** (chart, court, graphic) that tells the story at a glance
2. **1-2 data callouts** overlaid that add context

This is the Kirk Goldsberry / datakabas approach - the chart IS the content, with key numbers highlighted.

**Target:** 3-5 posts/week. Python for data, Figma/Canva for polish.

**Priority formats:** Post-game shot charts and single stat player posts.

---

## Current Data Capabilities

**What's available now:**
- Game logs, box scores, player game-by-game stats
- Shot chart data (location, zone, distance, made/missed)
- League-wide shot data for all 30 teams
- Points Per Shot (PPS) analysis by zone
- Shot selection quality metrics
- Efficiency metrics (TS%, eFG%)
- Rolling averages and consistency scores
- Scoring trends (direction, comparison)

**Key findings from existing analysis:**
- Bulls rank #1 in shot selection (78.7% high-value shots)
- Bulls rank #28 at the rim (Restricted Area efficiency)
- Bulls rank #4 in right corner 3 efficiency (90th percentile)
- Bulls are -91 points vs league-average execution this season

---

## Format 1: Post-Game Shot Charts (Recurring)

**After every game** - consistent cadence, builds habit.

### Variations:

**A) Team Shot Chart + Zone Callouts**
- Full team shot chart (makes/misses)
- Circle 1-2 hot/cold zones with callout: "12/18 from Restricted Area" or "1/7 from mid-range"
- Caption: brief game context

**B) Star Player Breakdown**
- Isolate top scorer's shots only
- Callout: "Coby White: 8/12 FG, 4/6 from 3"
- Show where they hurt the opponent

**C) Tonight vs Season Average**
- Split visual or overlay
- "Tonight: 48% from 3 (Season: 36%)"
- Highlight the deviation

**Data sources:**
- `get_team_shots()` or `get_player_shots()`
- `shot_chart()` for visual
- `points_per_shot()` for zone efficiency

---

## Format 2: Player Stat Spotlight

**One player. One visual. One insight.**

### Examples:

**A) Zone Dominance**
- Player headshot + shot chart of THEIR shots only
- Callout: "Josh Giddey: 65% at the rim (Team high)"
- Visual shows the cluster of makes in that zone

**B) Efficiency Snapshot**
- Player photo + efficiency number
- Callout: "Coby White: 58.2% TS (Above league avg 57.1%)"
- Simple bar or gauge visual showing where they stand

**C) Hot Streak / Cold Streak**
- Line chart of last 5-10 games
- Callout: "Scoring up 4.2 PPG over last 5"
- Visual shows the trend direction

**Data sources:**
- `get_player_shots()` for shot chart
- `efficiency_metrics()` for TS%/eFG%
- `scoring_trend()` for direction
- `rolling_averages()` for trend line

---

## Format 3: League Context Posts (Weekly)

**Where Bulls stand** - gives fans perspective.

### Examples:

**A) Zone Ranking**
- Court visual with ONE zone highlighted
- Callout: "Bulls: #4 in Right Corner 3 efficiency"
- Top 5 teams listed below

**B) Efficiency Ranking**
- Bar chart of top 10 teams in a metric
- Bulls bar highlighted in red
- Callout: "Bulls: #1 in shot selection (78.7% high-value)"

**Data sources:**
- `league_pps_by_zone()`
- `team_zone_comparison()`
- `high_value_zone_usage()`

---

## Concrete Post Examples (With Mockups)

### Example 1: Post-Game Shot Chart

**Visual:** Half-court with green dots (makes) and red X's (misses)

```
┌─────────────────────────────────┐
│                                 │
│   "Bulls vs [Opponent]"         │
│                                 │
│   [SHOT CHART VISUAL]           │
│   Green = makes, Red = misses   │
│                                 │
│   ┌──────────────────────────┐  │
│   │ "12/18 in the paint"     │  │  ← Callout overlay
│   └──────────────────────────┘  │
│                                 │
│   ┌──────────────────────────┐  │
│   │ "5/14 from 3 (35.7%)"    │  │  ← Callout overlay
│   └──────────────────────────┘  │
│                                 │
└─────────────────────────────────┘
```

Caption: "Bulls shot 47% overall but only 35% from 3. The paint was the story tonight."

---

### Example 2: Player Spotlight - Zone Dominance

**Visual:** Player shot chart (their shots only) with key zone circled

```
┌─────────────────────────────────┐
│                                 │
│   "GIDDEY AT THE RIM"           │
│                                 │
│   [PLAYER HEADSHOT]             │
│                                 │
│   [SHOT CHART - his shots only] │
│        ┌───────┐                │
│        │ 6.28  │  ← Callout     │
│        │ PPG   │                │
│        └───────┘                │
│                                 │
│   "Leads Bulls in Restricted    │
│    Area scoring"                │
│                                 │
└─────────────────────────────────┘
```

Caption: "Josh Giddey leads the Bulls at the rim with 6.28 PPG in the Restricted Area. His finishing around the basket has been elite."

---

### Example 3: Player Spotlight - Shooter Profile

**Visual:** Shot chart with 3-point zones highlighted

```
┌─────────────────────────────────┐
│                                 │
│   "COBY'S RANGE"                │
│                                 │
│   [SHOT CHART - Coby's shots]   │
│                                 │
│   Above the break highlighted   │
│        ┌──────────────┐         │
│        │  5.85 PPG    │         │
│        │  from deep   │         │
│        └──────────────┘         │
│                                 │
│   "Team leader: Above Break 3"  │
│                                 │
└─────────────────────────────────┘
```

Caption: "Coby White owns the arc. 5.85 PPG from above the break 3 - leading the Bulls by a wide margin."

---

### Example 4: Tonight vs Season (Post-Game Variant)

**Visual:** Side-by-side or overlay comparison

```
┌─────────────────────────────────┐
│                                 │
│   "TONIGHT vs SEASON"           │
│                                 │
│   ┌─────────┐   ┌─────────┐     │
│   │ TONIGHT │   │ SEASON  │     │
│   │ 48% FG  │   │ 44% FG  │     │
│   │  ▲ +4%  │   │         │     │
│   └─────────┘   └─────────┘     │
│                                 │
│   ┌─────────┐   ┌─────────┐     │
│   │ 42% 3PT │   │ 34% 3PT │     │
│   │  ▲ +8%  │   │         │     │
│   └─────────┘   └─────────┘     │
│                                 │
│   "Hot shooting night"          │
│                                 │
└─────────────────────────────────┘
```

Caption: "Bulls shot it well tonight. 48% from the field (season: 44%) and 42% from 3 (season: 34%). The hottest they've looked in weeks."

---

### Example 5: League Context - Simple Rank

**Visual:** Bar chart with Bulls highlighted in red

```
┌─────────────────────────────────┐
│                                 │
│   "RIGHT CORNER 3"              │
│   League Efficiency Ranking     │
│                                 │
│   1. Celtics    ████████ 1.52   │
│   2. Warriors   ███████░ 1.48   │
│   3. Heat       ██████░░ 1.44   │
│   4. BULLS      ██████░░ 1.42   │  ← Red bar
│   5. Nuggets    █████░░░ 1.38   │
│                                 │
│   ┌──────────────────────────┐  │
│   │ Bulls: #4 in the league  │  │
│   └──────────────────────────┘  │
│                                 │
└─────────────────────────────────┘
```

Caption: "Bulls are elite from the right corner. #4 in the league at 1.42 PPS. Ayo Dosunmu leads the team from that spot."

---

## Additional Content Ideas (Analytics Deep Dives)

### Concept 1: "The Modern Player Test"

**The insight:** Daryl Morey basketball says only shoot 3s and layups. Who on the Bulls actually plays that way?

**Visual:** Player list with % of shots from high-value zones (Restricted + 3PT)

```
High-Value Shot Selection:
1. Julian Phillips   95.9%  ████████████████████
2. Patrick Williams  88.2%  ██████████████████░░
3. Matas Buzelis     84.1%  █████████████████░░░
...
10. Nikola Vučević   57.3%  ███████████░░░░░░░░░
```

**Callout:** "Julian Phillips shoots like an analytics dream. Vučević? Not so much."

**Why it works:**
- Casuals: Simple percentage, clear ranking
- Data heads: Shot selection quality is real analytics
- Hot take fuel: Vučević's mid-range game is controversial

**Data:** `high_value_zone_usage()` - already exists!

---

### Concept 2: "Volume vs Efficiency" Quadrant

**The insight:** Classic scatter plot - who earns their shots?

**Visual:** 4-quadrant scatter plot

```
           High Efficiency
                │
    "Specialists"  │  "Stars"
    (low volume,   │  (high volume,
     high return)  │   high return)
    ───────────────┼───────────────
    "Bricks"       │  "Chuckers"
    (low volume,   │  (high volume,
     low return)   │   low return)
                │
           Low Efficiency
```

**Callout:** Player dots labeled, quadrant labels visible

**Why it works:**
- Casuals: "Stars" vs "Chuckers" is immediately understandable
- Data heads: Volume/efficiency tradeoff is fundamental
- Controversial: Shows who maybe shouldn't be shooting as much

**Data:** `season_averages()` + `efficiency_metrics()` - exists!

---

### Concept 3: "The Streak" / Form Check

**The insight:** Last 5 games vs previous 5 - who's trending?

**Visual:** Green/red block grid showing hot/cold

```
Last 10 Games:
Coby White  [🟢][🟢][🟢][🔴][🟢][🟢][🟢][🟢][🔴][🟢]  ▲ +4.2 PPG
Giddey      [🔴][🟢][🟢][🟢][🔴][🔴][🟢][🟢][🟢][🔴]  → Stable
Vučević     [🟢][🔴][🔴][🔴][🟢][🔴][🔴][🟢][🔴][🔴]  ▼ -3.1 PPG
```

**Callout:** "Coby is HOT. Vučević is ice cold."

**Why it works:**
- Casuals: Green = good, red = bad. Obvious trend.
- Data heads: Rolling averages, trend direction
- Timely: Can post weekly to show who's heating up

**Data:** `scoring_trend()` + `rolling_averages()` - exists!

---

### Concept 4: "Consistency Score"

**The insight:** Who can you count on? Standard deviation matters.

**Visual:** Player cards showing mean ± volatility

```
COBY WHITE
────────────
PPG:  18.2 ± 6.1
      ▓▓▓▓▓▓░░░░  "Volatile"

JOSH GIDDEY
────────────
PPG:  14.8 ± 3.2
      ▓▓▓▓▓▓▓▓░░  "Consistent"
```

**Callout:** "Giddey gives you 12-18 every night. Coby might give you 8 or 28."

**Why it works:**
- Casuals: "You know what you're getting" is relatable
- Data heads: CV (coefficient of variation) is real stat
- Narrative: Consistency vs explosiveness is an interesting tension

**Data:** `consistency_score()` - exists!

---

### Concept 5: "Percentile Bars"

**The insight:** Where does a player rank league-wide? Top 10%? Bottom 20%?

**Visual:** Horizontal bar showing percentile

```
COBY WHITE - True Shooting %

League Distribution:
|░░░░░░░░░░░░░░░░░░▓░░|
                   ^
                  72nd percentile
                  "Above Average"
```

**Callout:** "Coby shoots better than 72% of the league by TS%."

**Why it works:**
- Casuals: Percentile is intuitive - "better than X% of players"
- Data heads: Context against league distribution
- Flexible: Works for any stat

**Data:** Need to add league context, but `efficiency_metrics()` gives the base

---

### Concept 6: "The Efficiency Gap"

**The insight:** If you shot league average from each zone, how many more/fewer points would you have?

**Visual:** Zone map with +/- annotations

```
           ┌────────────────────┐
           │  Above Break 3     │
           │     -8 pts         │  ← Below avg
           └────────────────────┘
    ┌───────┐             ┌───────┐
    │ LC3   │             │ RC3   │
    │ +3 pts│             │ +5 pts│  ← Above avg!
    └───────┘             └───────┘
              ┌─────────┐
              │  Rim    │
              │ -14 pts │  ← Big problem
              └─────────┘
```

**Callout:** "Bulls are leaving 14 points on the table at the rim."

**Why it works:**
- Casuals: Points left on table is visceral
- Data heads: Expected vs actual is core analytics
- Actionable: Shows where to improve

**Data:** `team_zone_comparison()` + league averages - exists!

---

### Concept 7: "Shot Diet" Pie Charts

**The insight:** Where does each player get their shots? Are they eating healthy?

**Visual:** Simple pie/donut chart per player

```
JULIAN PHILLIPS
Shot Diet:
[Rim 60%][3PT 36%][Mid 4%]
         ▲ Analytics-approved

NIKOLA VUČEVIĆ
Shot Diet:
[Rim 28%][3PT 20%][Mid 52%]
         ▲ Old school
```

**Callout:** "Phillips plays modern basketball. Vučević is from 2008."

**Why it works:**
- Casuals: Pie chart is simple
- Data heads: Shot selection is everything
- Generational: Old vs new basketball styles

**Data:** Calculate from `get_player_shots()` zone distribution

---

### Concept 8: "Clutch Check" (Future - needs data)

**The insight:** Who shows up in crunch time?

**Visual:** Last 2 minutes, score within 5 points

```
CLUTCH STATS (Final 2 min, ±5 pts)
                FG%    PTS
Coby White      42%    2.1
Ayo Dosunmu     38%    1.4
Josh Giddey     33%    0.8
```

**Callout:** "When it's tight, Coby gets the ball."

**Why it works:**
- Casuals: Clutch is universally understood
- Data heads: Small sample but emotionally resonant
- Narrative: Who's the closer?

**Data:** Would need `get_clutch_shots()` - not built yet

---

### Concept 9: "The Matchup Effect"

**The insight:** Who do the Bulls destroy? Who kills them?

**Visual:** Shot efficiency vs specific opponents

```
Bulls Restricted Area FG%:
vs Pistons:   72%  ████████████████
vs Celtics:   48%  ██████████░░░░░░
vs Pacers:    68%  ██████████████░░
```

**Callout:** "The Bulls feast at the rim against Detroit."

**Why it works:**
- Casuals: Matchups are sports 101
- Data heads: Opponent adjustment is real
- Timely: Post before games vs that team

**Data:** Filter `get_team_shots()` by game_id/opponent - doable with current data

---

### Concept 10: "Then vs Now"

**The insight:** Season progression - are they improving?

**Visual:** First 20 games vs last 20 games comparison

```
BULLS SHOT PROFILE
            First 20    Last 20
3PA Share:    34%   →    38%
Rim Share:    32%   →    35%
Mid-Range:    34%   →    27%  ▼
```

**Callout:** "The Bulls are learning. Mid-range shots are dying."

**Why it works:**
- Casuals: Progress/regression is narrative
- Data heads: Sample size evolution
- Optimistic/pessimistic: Shows direction

**Data:** Split by date range - doable

---

## Specific Post Ideas (Ready to Create)

### Post-Game Series
1. **"Zone Breakdown"** - Team shot chart with 2-3 zone stats overlaid
2. **"Player of the Night"** - Top scorer's shot chart isolated
3. **"The Story of the Game"** - One zone that defined win/loss

### Player Spotlights
4. **"Giddey at the Rim"** - His restricted area dominance (6.28 PPG, 65%)
5. **"Coby's Range"** - Shot chart showing his 3-point distribution
6. **"Julian Phillips: Modern Player"** - 95.9% high-value shots visual
7. **"Vučević's Mid-Range"** - The exception to the analytics rule

### League Context
8. **"Right Corner Snipers"** - Bulls #4 ranking with top 5 teams
9. **"Shot Selection Kings"** - Bulls #1 with league comparison
10. **"The Rim Problem"** - Bulls #28 at rim, what it looks like

---

## Weekly Cadence

| Day | Format | Content |
|-----|--------|---------|
| Game nights | Post-game shot chart | Zone breakdown or player spotlight |
| Mid-week | Player stat spotlight | Trending player or deep dive |
| Weekend | League context | Bulls vs league ranking |

---

## What Makes These Work

1. **Visual-first** - The chart/graphic tells the story, not the text
2. **1-2 callouts max** - Key numbers overlaid on the visual
3. **Context in caption** - Explanation goes in the caption, not the graphic
4. **One insight** - Each post has ONE takeaway

---

## Production Workflow

### For Post-Game Content (Quick Turnaround)

1. Run `get_team_shots()` filtered to that game
2. Generate `shot_chart()`
3. Calculate zone breakdowns manually or add helper function
4. Export PNG from Python
5. Add callouts in Figma/Canva
6. Post with caption

### For Player Spotlights (Planned Content)

1. Run `get_player_shots()` for target player
2. Generate their shot chart
3. Get `zone_leaders()` data for context
4. Create base visual in Python
5. Polish in Figma with headshot, callouts, branding
6. Schedule post

### For League Rankings (Weekly)

1. Run `league_pps_by_zone()` (takes longer - 30 teams)
2. Extract Bulls ranking for target zone
3. Create bar chart with top 5-10 teams
4. Highlight Bulls bar
5. Add callout with rank
6. Polish and post

---

## Implementation Priority

### Idea Categories

| Type | Effort | Examples |
|------|--------|----------|
| **Exists now** | Low | Modern Player Test, Streak, Consistency, Vol/Eff quadrant |
| **Light build** | Medium | Efficiency Gap, Shot Diet, Then vs Now, Matchup Effect |
| **Needs new data** | High | Clutch Check, Play Types, Defensive stats |

### Quick Wins (Current Data)

1. Zone Leaders / Winner by Bucket
2. Post-game shot charts
3. Team identity map (3PA vs rim share)
4. Bulls vs League heatmap
5. The Modern Player Test (shot selection)
6. Form Check / Streak tracker

### Requires New Data

1. Clutch analysis
2. Play type breakdowns
3. Historical comparisons

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

## Example Post in Practice

**"Coby's 30-Piece"**

Visual: Coby's shot chart from the game
Callouts:
- "12/20 FG"
- "6/9 from 3"
- Circle the left wing where he hit 4/5

Caption: "Coby White dropped 30 on [Opponent]. His shot selection: 75% from high-value zones. The left wing was his office tonight."
