# StatsBomb 2023 Radar Metrics - Query Implementation Plan

**Date:** October 20, 2025
**Purpose:** Map StatsBomb 2023 radar metrics to BigQuery SQL queries using our FIFA events dataset

---

## Table of Contents
1. [Metrics We CAN Calculate](#metrics-we-can-calculate)
2. [Metrics We CANNOT Calculate (Missing OBV)](#metrics-we-cannot-calculate-missing-obv)
3. [Position-Specific Radar Queries](#position-specific-radar-queries)
4. [Possession Adjustment Formula](#possession-adjustment-formula)

---

## Overview

StatsBomb 2023 radars are position-specific and use **On Ball Value (OBV)** heavily. Our dataset **does not include OBV**, so we'll need to create **alternative versions** using available metrics that correlate with player performance.

**Key Challenge:** OBV is StatsBomb's proprietary metric. We'll substitute with:
- Shot xG for "Shot OBV"
- Pass completion/assist metrics for "Pass OBV"
- Successful defensive actions for "Defensive Action OBV"
- Successful dribbles/carries for "Dribble & Carry OBV"

---

## Metrics We CAN Calculate

### ✅ 1. **xG (Non-Penalty)**
**Definition:** Non-penalty expected goals produced by the player
**StatsBomb Usage:** Strikers, Attacking Midfielders & Wingers

```sql
-- Player Non-Penalty xG
SELECT
    player,
    team,
    SUM(CASE WHEN type = 'Shot' AND shot_type != 'Penalty'
        THEN shot_statsbomb_xg ELSE 0.0 END) as non_penalty_xg,
    COUNT(DISTINCT match_id) as matches_played,
    SUM(CASE WHEN type = 'Shot' AND shot_type != 'Penalty'
        THEN shot_statsbomb_xg ELSE 0.0 END) / COUNT(DISTINCT match_id) as xg_per_90
FROM events
WHERE player = @player_name
  AND team = @team_name
GROUP BY player, team
```

**Data Available:** ✅ `shot_statsbomb_xg`, `shot_type`

---

### ✅ 2. **Shots (Non-Penalty)**
**Definition:** Number of non-penalty shots a player takes
**StatsBomb Usage:** Strikers, Attacking Midfielders & Wingers

```sql
-- Player Non-Penalty Shots
SELECT
    player,
    team,
    COUNTIF(type = 'Shot' AND shot_type != 'Penalty') as non_penalty_shots,
    COUNT(DISTINCT match_id) as matches_played,
    COUNTIF(type = 'Shot' AND shot_type != 'Penalty') / COUNT(DISTINCT match_id) as shots_per_90
FROM events
WHERE player = @player_name
  AND team = @team_name
GROUP BY player, team
```

**Data Available:** ✅ `type`, `shot_type`

---

### ✅ 3. **xG/Shot**
**Definition:** The average non-penalty expected goal value per shot a player takes
**StatsBomb Usage:** Strikers, Attacking Midfielders & Wingers

```sql
-- Player xG per Shot
SELECT
    player,
    team,
    SUM(CASE WHEN type = 'Shot' AND shot_type != 'Penalty'
        THEN shot_statsbomb_xg ELSE 0.0 END) /
        NULLIF(COUNTIF(type = 'Shot' AND shot_type != 'Penalty'), 0) as xg_per_shot
FROM events
WHERE player = @player_name
  AND team = @team_name
GROUP BY player, team
```

**Data Available:** ✅ `shot_statsbomb_xg`, `shot_type`

---

### ✅ 4. **Open Play xG Assisted**
**Definition:** xG assisted from open play
**StatsBomb Usage:** All outfield positions (especially creative players)

```sql
-- Open Play xG Assisted
WITH assisted_shots AS (
    SELECT
        e1.player as assister,
        e1.team,
        e1.match_id,
        e2.shot_statsbomb_xg,
        e2.shot_type,
        e1.play_pattern
    FROM events e1
    INNER JOIN events e2
        ON e1.pass_assisted_shot_id = e2.id
    WHERE e1.type = 'Pass'
      AND e1.pass_shot_assist = TRUE
      AND e2.type = 'Shot'
)
SELECT
    assister as player,
    team,
    SUM(CASE
        WHEN shot_type != 'Penalty'
         AND play_pattern NOT IN ('From Corner', 'From Free Kick')
        THEN shot_statsbomb_xg
        ELSE 0.0
    END) as open_play_xg_assisted,
    COUNT(DISTINCT match_id) as matches_played
FROM assisted_shots
WHERE assister = @player_name
  AND team = @team_name
GROUP BY assister, team
```

**Data Available:** ✅ `pass_assisted_shot_id`, `pass_shot_assist`, `play_pattern`

---

### ✅ 5. **Deep Progressions**
**Definition:** Passes and dribbles/carries into the opposition final third
**StatsBomb Usage:** Full Backs, Midfielders

```sql
-- Deep Progressions (Final Third Entries)
SELECT
    player,
    team,
    -- Progressive passes into final third
    COUNTIF(type = 'Pass' AND pass_outcome IS NULL
        AND x < 80 AND pass_end_location[OFFSET(0)] >= 80) as progressive_passes,
    -- Progressive carries into final third
    COUNTIF(type = 'Carry'
        AND x < 80 AND carry_end_location[OFFSET(0)] >= 80) as progressive_carries,
    -- Total deep progressions
    COUNTIF(
        (type = 'Pass' AND pass_outcome IS NULL AND x < 80 AND pass_end_location[OFFSET(0)] >= 80)
        OR (type = 'Carry' AND x < 80 AND carry_end_location[OFFSET(0)] >= 80)
    ) as deep_progressions,
    COUNT(DISTINCT match_id) as matches_played
FROM events
WHERE player = @player_name
  AND team = @team_name
  AND (
      (type = 'Pass' AND pass_end_location IS NOT NULL)
      OR (type = 'Carry' AND carry_end_location IS NOT NULL)
  )
GROUP BY player, team
```

**Data Available:** ✅ `x`, `pass_end_location`, `carry_end_location`
**Note:** StatsBomb pitch coordinates: attacking direction goes toward x=120

---

### ✅ 6. **Touches In Box**
**Definition:** Successful footed touches inside the box (including shots)
**StatsBomb Usage:** Strikers, Attacking Midfielders & Wingers

```sql
-- Touches in Opposition Box
SELECT
    player,
    team,
    COUNTIF(
        x >= 102 AND x <= 120  -- Opposition penalty box
        AND y >= 18 AND y <= 62  -- Box width
        AND type IN (
            'Pass', 'Ball Receipt*', 'Carry', 'Shot', 'Dribble',
            'Duel', 'Clearance', 'Miscontrol', 'Dispossessed'
        )
    ) as touches_in_box,
    COUNT(DISTINCT match_id) as matches_played
FROM events
WHERE player = @player_name
  AND team = @team_name
  AND x IS NOT NULL
  AND y IS NOT NULL
GROUP BY player, team
```

**Data Available:** ✅ `x`, `y`, `type`
**Note:** Opposition box coordinates: x ∈ [102, 120], y ∈ [18, 62]

---

### ✅ 7. **Aerial Wins**
**Definition:** Number of aerial duels a player wins
**StatsBomb Usage:** Centre Backs, Full Backs, Strikers

```sql
-- Aerial Duels Won
SELECT
    player,
    team,
    -- Aerial duels won
    COUNTIF(duel_type = 'Aerial Lost' AND duel_outcome IN ('Won', 'Success In Play', 'Success Out')) as aerial_wins,
    -- Total aerial duels
    COUNTIF(duel_type = 'Aerial Lost') as aerial_duels,
    -- Aerial win percentage
    SAFE_DIVIDE(
        COUNTIF(duel_type = 'Aerial Lost' AND duel_outcome IN ('Won', 'Success In Play', 'Success Out')) * 100.0,
        NULLIF(COUNTIF(duel_type = 'Aerial Lost'), 0)
    ) as aerial_win_percentage,
    COUNT(DISTINCT match_id) as matches_played
FROM events
WHERE player = @player_name
  AND team = @team_name
GROUP BY player, team
```

**Data Available:** ✅ `duel_type`, `duel_outcome`

---

### ✅ 8. **Aerial Win %**
**Definition:** Percentage of aerial duels a player enters that they win
**StatsBomb Usage:** Centre Backs, Full Backs

```sql
-- See query above (#7)
```

---

### ✅ 9. **Turnovers**
**Definition:** How often a player loses the ball via a miscontrol or a failed dribble
**StatsBomb Usage:** All outfield positions

```sql
-- Turnovers (Miscontrols + Failed Dribbles)
SELECT
    player,
    team,
    -- Miscontrols
    COUNTIF(type = 'Miscontrol') as miscontrols,
    -- Failed dribbles
    COUNTIF(type = 'Dribble' AND dribble_outcome = 'Incomplete') as failed_dribbles,
    -- Dispossessed events
    COUNTIF(type = 'Dispossessed') as dispossessed,
    -- Total turnovers
    COUNTIF(
        type IN ('Miscontrol', 'Dispossessed')
        OR (type = 'Dribble' AND dribble_outcome = 'Incomplete')
    ) as total_turnovers,
    COUNT(DISTINCT match_id) as matches_played
FROM events
WHERE player = @player_name
  AND team = @team_name
GROUP BY player, team
```

**Data Available:** ✅ `type`, `dribble_outcome`

---

### ✅ 10. **Fouls Won**
**Definition:** How many times a player is fouled
**StatsBomb Usage:** Midfielders, Attacking Midfielders & Wingers

```sql
-- Fouls Won by Player
SELECT
    player,
    team,
    COUNTIF(type = 'Foul Won') as fouls_won,
    COUNTIF(type = 'Foul Won' AND foul_won_penalty = TRUE) as penalties_won,
    COUNT(DISTINCT match_id) as matches_played
FROM events
WHERE player = @player_name
  AND team = @team_name
GROUP BY player, team
```

**Data Available:** ✅ `type`, `foul_won_penalty`

---

### ✅ 11. **Fouls (Committed)**
**Definition:** How many fouls a player commits
**StatsBomb Usage:** Centre Backs, Full Backs

```sql
-- Fouls Committed by Player
SELECT
    player,
    team,
    COUNTIF(type = 'Foul Committed') as fouls_committed,
    COUNTIF(foul_committed_card IS NOT NULL) as fouls_with_card,
    COUNTIF(foul_committed_card = 'Yellow Card') as yellow_cards,
    COUNTIF(foul_committed_card = 'Red Card') as red_cards,
    COUNT(DISTINCT match_id) as matches_played
FROM events
WHERE player = @player_name
  AND team = @team_name
GROUP BY player, team
```

**Data Available:** ✅ `type`, `foul_committed_card`

---

### ✅ 12. **PAdj Tackles & Interceptions**
**Definition:** Number of tackles and interceptions adjusted proportionally to the possession volume of a team
**StatsBomb Usage:** Full Backs, Midfielders

```sql
-- Possession-Adjusted Tackles & Interceptions
WITH team_possession AS (
    SELECT
        team,
        match_id,
        COUNT(*) as team_events,
        SUM(COUNT(*)) OVER (PARTITION BY match_id) as total_events,
        (COUNT(*) * 100.0) / SUM(COUNT(*)) OVER (PARTITION BY match_id) as possession_pct
    FROM events
    WHERE type NOT IN ('Starting XI', 'Tactical Shift', 'Half Start', 'Half End')
    GROUP BY team, match_id
),
player_defensive_actions AS (
    SELECT
        e.player,
        e.team,
        e.match_id,
        COUNTIF(e.type = 'Duel' AND e.duel_type = 'Tackle') as tackles,
        COUNTIF(e.type = 'Interception'
            AND e.interception_outcome IN ('Won', 'Success In Play', 'Success Out')) as interceptions
    FROM events e
    WHERE e.player = @player_name
      AND e.team = @team_name
    GROUP BY e.player, e.team, e.match_id
)
SELECT
    pda.player,
    pda.team,
    SUM(pda.tackles) as tackles,
    SUM(pda.interceptions) as interceptions,
    SUM(pda.tackles + pda.interceptions) as tackles_and_interceptions,
    -- Possession-adjusted: multiply by (100 / possession%)
    -- Lower possession = more defensive work expected
    SUM((pda.tackles + pda.interceptions) * (100.0 / NULLIF(tp.possession_pct, 0))) as padj_tackles_interceptions,
    COUNT(DISTINCT pda.match_id) as matches_played
FROM player_defensive_actions pda
LEFT JOIN team_possession tp
    ON pda.team = tp.team AND pda.match_id = tp.match_id
GROUP BY pda.player, pda.team
```

**Data Available:** ✅ All fields available
**Formula:** `adjusted = raw_count × (100 / team_possession%)`

---

### ✅ 13. **PAdj Pressures**
**Definition:** Number of pressures adjusted proportionally to the possession volume of a team
**StatsBomb Usage:** Full Backs, Midfielders, Attacking Midfielders & Wingers, Strikers

```sql
-- Possession-Adjusted Pressures
WITH team_possession AS (
    SELECT
        team,
        match_id,
        COUNT(*) as team_events,
        (COUNT(*) * 100.0) / SUM(COUNT(*)) OVER (PARTITION BY match_id) as possession_pct
    FROM events
    WHERE type NOT IN ('Starting XI', 'Tactical Shift', 'Half Start', 'Half End')
    GROUP BY team, match_id
),
player_pressures AS (
    SELECT
        e.player,
        e.team,
        e.match_id,
        COUNTIF(e.type = 'Pressure') as pressures
    FROM events e
    WHERE e.player = @player_name
      AND e.team = @team_name
    GROUP BY e.player, e.team, e.match_id
)
SELECT
    pp.player,
    pp.team,
    SUM(pp.pressures) as pressures,
    SUM(pp.pressures * (100.0 / NULLIF(tp.possession_pct, 0))) as padj_pressures,
    COUNT(DISTINCT pp.match_id) as matches_played
FROM player_pressures pp
LEFT JOIN team_possession tp
    ON pp.team = tp.team AND pp.match_id = tp.match_id
GROUP BY pp.player, pp.team
```

**Data Available:** ✅ `type = 'Pressure'`

---

### ✅ 14. **PAdj Clearances**
**Definition:** Number of clearances adjusted proportionally to the possession volume of a team
**StatsBomb Usage:** Centre Backs

```sql
-- Possession-Adjusted Clearances
WITH team_possession AS (
    SELECT
        team,
        match_id,
        (COUNT(*) * 100.0) / SUM(COUNT(*)) OVER (PARTITION BY match_id) as possession_pct
    FROM events
    WHERE type NOT IN ('Starting XI', 'Tactical Shift', 'Half Start', 'Half End')
    GROUP BY team, match_id
),
player_clearances AS (
    SELECT
        e.player,
        e.team,
        e.match_id,
        COUNTIF(e.type = 'Clearance') as clearances,
        COUNTIF(e.type = 'Clearance' AND e.clearance_aerial_won = TRUE) as aerial_clearances
    FROM events e
    WHERE e.player = @player_name
      AND e.team = @team_name
    GROUP BY e.player, e.team, e.match_id
)
SELECT
    pc.player,
    pc.team,
    SUM(pc.clearances) as clearances,
    SUM(pc.aerial_clearances) as aerial_clearances,
    SUM(pc.clearances * (100.0 / NULLIF(tp.possession_pct, 0))) as padj_clearances,
    COUNT(DISTINCT pc.match_id) as matches_played
FROM player_clearances pc
LEFT JOIN team_possession tp
    ON pc.team = tp.team AND pc.match_id = tp.match_id
GROUP BY pc.player, pc.team
```

**Data Available:** ✅ `type = 'Clearance'`, `clearance_aerial_won`

---

### ✅ 15. **Blocks/Shot**
**Definition:** Blocks made per shot faced
**StatsBomb Usage:** Centre Backs

```sql
-- Blocks per Shot Faced
WITH team_shots_faced AS (
    SELECT
        team,
        match_id,
        COUNTIF(type = 'Shot') as shots_faced
    FROM events
    WHERE team != @team_name
      AND match_id IN (
          SELECT DISTINCT match_id FROM events WHERE team = @team_name
      )
    GROUP BY team, match_id
),
player_blocks AS (
    SELECT
        e.player,
        e.team,
        e.match_id,
        COUNTIF(e.type = 'Block') as blocks
    FROM events e
    WHERE e.player = @player_name
      AND e.team = @team_name
    GROUP BY e.player, e.team, e.match_id
)
SELECT
    pb.player,
    pb.team,
    SUM(pb.blocks) as blocks,
    SUM(tsf.shots_faced) as shots_faced,
    SAFE_DIVIDE(SUM(pb.blocks), SUM(tsf.shots_faced)) as blocks_per_shot,
    COUNT(DISTINCT pb.match_id) as matches_played
FROM player_blocks pb
LEFT JOIN team_shots_faced tsf
    ON pb.match_id = tsf.match_id
GROUP BY pb.player, pb.team
```

**Data Available:** ✅ `type = 'Block'`, `type = 'Shot'`

---

### ✅ 16. **Tackle/Dribbled Past %**
**Definition:** Percentage of time a player makes a tackle when going into a duel vs getting dribbled past
**StatsBomb Usage:** All defensive positions

```sql
-- Tackle Success Rate (Tackles vs Dribbled Past)
SELECT
    player,
    team,
    COUNTIF(type = 'Duel' AND duel_type = 'Tackle'
        AND duel_outcome IN ('Won', 'Success In Play', 'Success Out')) as successful_tackles,
    COUNTIF(type = 'Dribbled Past') as dribbled_past,
    -- Tackle/(Tackle + Dribbled Past) %
    SAFE_DIVIDE(
        COUNTIF(type = 'Duel' AND duel_type = 'Tackle'
            AND duel_outcome IN ('Won', 'Success In Play', 'Success Out')) * 100.0,
        NULLIF(
            COUNTIF(type = 'Duel' AND duel_type = 'Tackle'
                AND duel_outcome IN ('Won', 'Success In Play', 'Success Out'))
            + COUNTIF(type = 'Dribbled Past'),
            0
        )
    ) as tackle_dribbled_past_pct,
    COUNT(DISTINCT match_id) as matches_played
FROM events
WHERE player = @player_name
  AND team = @team_name
GROUP BY player, team
```

**Data Available:** ✅ `type`, `duel_type`, `duel_outcome`

---

### ✅ 17. **Being Pressured Change in Pass %**
**Definition:** How does passing % change when under pressure? (Pressured Pass % - Overall Pass %)
**StatsBomb Usage:** Centre Backs

```sql
-- Pass Completion Rate Change Under Pressure
SELECT
    player,
    team,
    -- Overall pass completion
    COUNTIF(type = 'Pass' AND pass_outcome IS NULL) as completed_passes,
    COUNTIF(type = 'Pass') as total_passes,
    SAFE_DIVIDE(
        COUNTIF(type = 'Pass' AND pass_outcome IS NULL) * 100.0,
        NULLIF(COUNTIF(type = 'Pass'), 0)
    ) as overall_pass_pct,

    -- Pass completion under pressure
    COUNTIF(type = 'Pass' AND pass_outcome IS NULL AND under_pressure = TRUE) as completed_under_pressure,
    COUNTIF(type = 'Pass' AND under_pressure = TRUE) as passes_under_pressure,
    SAFE_DIVIDE(
        COUNTIF(type = 'Pass' AND pass_outcome IS NULL AND under_pressure = TRUE) * 100.0,
        NULLIF(COUNTIF(type = 'Pass' AND under_pressure = TRUE), 0)
    ) as under_pressure_pass_pct,

    -- Change in pass %
    SAFE_DIVIDE(
        COUNTIF(type = 'Pass' AND pass_outcome IS NULL AND under_pressure = TRUE) * 100.0,
        NULLIF(COUNTIF(type = 'Pass' AND under_pressure = TRUE), 0)
    ) - SAFE_DIVIDE(
        COUNTIF(type = 'Pass' AND pass_outcome IS NULL) * 100.0,
        NULLIF(COUNTIF(type = 'Pass'), 0)
    ) as pass_pct_change_under_pressure,

    COUNT(DISTINCT match_id) as matches_played
FROM events
WHERE player = @player_name
  AND team = @team_name
GROUP BY player, team
```

**Data Available:** ✅ `under_pressure`, `pass_outcome`

---

## Metrics We CANNOT Calculate (Missing OBV)

### ❌ **Shot OBV**
**Definition:** On Ball Value Added (net) from Shots
**Replacement:** Use **xG** as proxy

### ❌ **Pass OBV**
**Definition:** On Ball Value Added (net) from Passes
**Replacement:** Use **Open Play xG Assisted** + **Pass Completion %** + **Progressive Passes**

### ❌ **Dribble & Carry OBV**
**Definition:** On Ball Value Added (net) from Dribbles and Carries
**Replacement:** Use **Successful Dribbles** + **Progressive Carries**

### ❌ **Defensive Action OBV**
**Definition:** On Ball Value Added (net) from Defensive Actions
**Replacement:** Use **PAdj Tackles & Interceptions** + **Successful Pressures**

### ❌ **OBV (Total)**
**Definition:** On Ball Value Added (net) total (all event types)
**Replacement:** Aggregate of all replacement metrics above

### ❌ **Goalkeeper OBV**
**Definition:** On Ball Value Added (net) from goalkeeping actions
**Replacement:** Not feasible without OBV data

---

## Goalkeeper-Specific Metrics (Partial Support)

### ⚠️ **Long Ball %**
**Definition:** Percentage of attempted long balls that are actually completed

```sql
-- Goalkeeper Long Ball Completion
SELECT
    player,
    team,
    COUNTIF(type = 'Pass' AND position = 'Goalkeeper'
        AND pass_length >= 30 AND pass_outcome IS NULL) as long_balls_completed,
    COUNTIF(type = 'Pass' AND position = 'Goalkeeper'
        AND pass_length >= 30) as long_balls_attempted,
    SAFE_DIVIDE(
        COUNTIF(type = 'Pass' AND position = 'Goalkeeper'
            AND pass_length >= 30 AND pass_outcome IS NULL) * 100.0,
        NULLIF(COUNTIF(type = 'Pass' AND position = 'Goalkeeper'
            AND pass_length >= 30), 0)
    ) as long_ball_pct
FROM events
WHERE player = @player_name
  AND team = @team_name
  AND position = 'Goalkeeper'
GROUP BY player, team
```

**Data Available:** ✅ `pass_length`, `position`
**Note:** "Long ball" threshold is subjective; using 30 yards as proxy

---

### ⚠️ **Pass Into Danger %**
**Definition:** Percentage of passes made where the recipient was deemed to be under pressure or was next engaged with a defensive action

```sql
-- Pass Into Danger (Recipient Under Pressure)
WITH pass_recipient_next_event AS (
    SELECT
        e1.player as passer,
        e1.team,
        e1.match_id,
        e1.pass_recipient,
        e2.under_pressure as recipient_under_pressure,
        e2.type as recipient_next_event_type,
        e1.id as pass_id
    FROM events e1
    LEFT JOIN events e2
        ON e1.match_id = e2.match_id
        AND e1.pass_recipient = e2.player
        AND e2.index = e1.index + 1  -- Next event
    WHERE e1.type = 'Pass'
      AND e1.pass_outcome IS NULL  -- Successful pass
)
SELECT
    passer as player,
    team,
    COUNTIF(
        recipient_under_pressure = TRUE
        OR recipient_next_event_type IN ('Duel', 'Pressure', 'Dispossessed', 'Miscontrol')
    ) as passes_into_danger,
    COUNT(*) as total_passes,
    SAFE_DIVIDE(
        COUNTIF(
            recipient_under_pressure = TRUE
            OR recipient_next_event_type IN ('Duel', 'Pressure', 'Dispossessed', 'Miscontrol')
        ) * 100.0,
        COUNT(*)
    ) as pass_into_danger_pct
FROM pass_recipient_next_event
WHERE passer = @player_name
  AND team = @team_name
GROUP BY passer, team
```

**Data Available:** ⚠️ Partial - requires event sequencing
**Challenge:** May not perfectly match StatsBomb's definition of "danger"

---

### ❌ **Claims - CCAA %**
**Data Unavailable:** Requires "claimable pass" classification not in our data

### ❌ **Goalkeeper Aggressive Distance**
**Data Unavailable:** Requires goalkeeper positioning data not in our dataset

### ❌ **Positioning Error**
**Data Unavailable:** Requires optimal position calculation (StatsBomb proprietary)

### ❌ **Shot Stopping %**
**Data Unavailable:** Requires post-shot xG (PSxG) which we don't have

---

## Position-Specific Radar Queries

### 🔷 **Goalkeeper Radar (Limited)**

**Metrics Available:**
1. Long Ball % ⚠️
2. Pass Into Danger % ⚠️
3. ~~Goalkeeper OBV~~ ❌
4. ~~Claims - CCAA %~~ ❌
5. ~~Goalkeeper Aggressive Distance~~ ❌
6. ~~Positioning Error~~ ❌
7. ~~Shot Stopping %~~ ❌

**Recommendation:** Goalkeeper radars are **not feasible** with current data due to missing specialized metrics.

---

### 🔷 **Centre Back Radar**

**Metrics Available:**
1. ✅ Aerial Win %
2. ✅ Aerial Wins
3. ~~OBV~~ → Use Replacement
4. ~~Pass OBV~~ → **Pass Completion %** + **Progressive Passes**
5. ✅ Being Pressured Change in Pass %
6. ~~Dribble & Carry OBV~~ → **Successful Dribbles** + **Progressive Carries**
7. ✅ Fouls
8. ✅ PAdj Clearances
9. ✅ Blocks/Shot
10. ✅ Tackle/Dribbled Past %
11. ~~Defensive Action OBV~~ → **PAdj Tackles & Interceptions**

**Consolidated Query:**

```sql
-- Centre Back Radar Metrics
WITH team_possession AS (
    SELECT
        team,
        match_id,
        (COUNT(*) * 100.0) / SUM(COUNT(*)) OVER (PARTITION BY match_id) as possession_pct
    FROM events
    WHERE type NOT IN ('Starting XI', 'Tactical Shift', 'Half Start', 'Half End')
    GROUP BY team, match_id
),
team_shots_faced AS (
    SELECT
        e1.team as defending_team,
        e1.match_id,
        COUNTIF(e2.type = 'Shot') as shots_faced
    FROM (SELECT DISTINCT team, match_id FROM events WHERE team = @team_name) e1
    LEFT JOIN events e2
        ON e1.match_id = e2.match_id AND e2.team != e1.team
    GROUP BY e1.team, e1.match_id
),
player_metrics AS (
    SELECT
        e.player,
        e.team,
        e.match_id,

        -- Aerial duels
        COUNTIF(e.duel_type = 'Aerial Lost' AND e.duel_outcome IN ('Won', 'Success In Play', 'Success Out')) as aerial_wins,
        COUNTIF(e.duel_type = 'Aerial Lost') as aerial_duels,

        -- Passes
        COUNTIF(e.type = 'Pass' AND e.pass_outcome IS NULL) as completed_passes,
        COUNTIF(e.type = 'Pass') as total_passes,
        COUNTIF(e.type = 'Pass' AND e.pass_outcome IS NULL AND e.under_pressure = TRUE) as passes_under_pressure_completed,
        COUNTIF(e.type = 'Pass' AND e.under_pressure = TRUE) as passes_under_pressure,

        -- Progressive passes
        COUNTIF(e.type = 'Pass' AND e.pass_outcome IS NULL
            AND e.x < 80 AND e.pass_end_location[OFFSET(0)] >= 80) as progressive_passes,

        -- Dribbles and carries
        COUNTIF(e.type = 'Dribble' AND e.dribble_outcome = 'Complete') as successful_dribbles,
        COUNTIF(e.type = 'Carry' AND e.x < 80 AND e.carry_end_location[OFFSET(0)] >= 80) as progressive_carries,

        -- Fouls
        COUNTIF(e.type = 'Foul Committed') as fouls_committed,

        -- Clearances
        COUNTIF(e.type = 'Clearance') as clearances,

        -- Blocks
        COUNTIF(e.type = 'Block') as blocks,

        -- Tackles & Interceptions
        COUNTIF(e.type = 'Duel' AND e.duel_type = 'Tackle') as tackles,
        COUNTIF(e.type = 'Interception' AND e.interception_outcome IN ('Won', 'Success In Play', 'Success Out')) as interceptions,

        -- Tackle vs Dribbled Past
        COUNTIF(e.type = 'Duel' AND e.duel_type = 'Tackle'
            AND e.duel_outcome IN ('Won', 'Success In Play', 'Success Out')) as successful_tackles,
        COUNTIF(e.type = 'Dribbled Past') as dribbled_past

    FROM events e
    WHERE e.player = @player_name
      AND e.team = @team_name
    GROUP BY e.player, e.team, e.match_id
)
SELECT
    pm.player,
    pm.team,
    COUNT(DISTINCT pm.match_id) as matches_played,

    -- 1. Aerial Win %
    SAFE_DIVIDE(SUM(pm.aerial_wins) * 100.0, NULLIF(SUM(pm.aerial_duels), 0)) as aerial_win_pct,

    -- 2. Aerial Wins
    SUM(pm.aerial_wins) as aerial_wins,

    -- 3. Pass Completion % (OBV replacement)
    SAFE_DIVIDE(SUM(pm.completed_passes) * 100.0, NULLIF(SUM(pm.total_passes), 0)) as pass_completion_pct,

    -- 4. Progressive Passes (Pass OBV replacement)
    SUM(pm.progressive_passes) as progressive_passes,

    -- 5. Being Pressured Change in Pass %
    SAFE_DIVIDE(SUM(pm.passes_under_pressure_completed) * 100.0, NULLIF(SUM(pm.passes_under_pressure), 0))
        - SAFE_DIVIDE(SUM(pm.completed_passes) * 100.0, NULLIF(SUM(pm.total_passes), 0)) as pass_pct_change_under_pressure,

    -- 6. Successful Dribbles + Progressive Carries (Dribble & Carry OBV replacement)
    SUM(pm.successful_dribbles) + SUM(pm.progressive_carries) as progressive_ball_advancement,

    -- 7. Fouls Committed
    SUM(pm.fouls_committed) as fouls_committed,

    -- 8. PAdj Clearances
    SUM(pm.clearances * (100.0 / NULLIF(tp.possession_pct, 0))) as padj_clearances,

    -- 9. Blocks/Shot
    SAFE_DIVIDE(SUM(pm.blocks), SUM(tsf.shots_faced)) as blocks_per_shot,

    -- 10. Tackle/Dribbled Past %
    SAFE_DIVIDE(
        SUM(pm.successful_tackles) * 100.0,
        NULLIF(SUM(pm.successful_tackles) + SUM(pm.dribbled_past), 0)
    ) as tackle_dribbled_past_pct,

    -- 11. PAdj Tackles & Interceptions (Defensive Action OBV replacement)
    SUM((pm.tackles + pm.interceptions) * (100.0 / NULLIF(tp.possession_pct, 0))) as padj_tackles_interceptions

FROM player_metrics pm
LEFT JOIN team_possession tp
    ON pm.team = tp.team AND pm.match_id = tp.match_id
LEFT JOIN team_shots_faced tsf
    ON pm.team = tsf.defending_team AND pm.match_id = tsf.match_id
GROUP BY pm.player, pm.team
```

---

### 🔷 **Full Back Radar**

**Metrics Available:**
1. ✅ PAdj Tackles & Interceptions
2. ✅ Deep Progressions
3. ~~Pass OBV~~ → **Progressive Passes** + **Open Play xG Assisted**
4. ✅ Open Play xG Assisted
5. ~~Dribble & Carry OBV~~ → **Successful Dribbles** + **Progressive Carries**
6. ✅ Turnovers
7. ✅ Aerial Win %
8. ✅ PAdj Pressures
9. ✅ Fouls
10. ✅ Tackle/Dribbled Past %
11. ~~Defensive Action OBV~~ → **PAdj Tackles & Interceptions**

---

### 🔷 **Midfielder Radar**

**Metrics Available:**
1. ~~OBV~~ → Composite score
2. ✅ Deep Progressions
3. ~~Pass OBV~~ → **Progressive Passes** + **Open Play xG Assisted**
4. ✅ Open Play xG Assisted
5. ~~Dribble & Carry OBV~~ → **Successful Dribbles** + **Progressive Carries**
6. ✅ Fouls Won
7. ✅ Turnovers
8. ✅ PAdj Pressures
9. ✅ PAdj Tackles & Interceptions
10. ✅ Tackle/Dribbled Past %
11. ~~Defensive Action OBV~~ → **PAdj Tackles & Interceptions**

---

### 🔷 **Attacking Midfielder & Winger Radar**

**Metrics Available:**
1. ✅ xG (Non-Penalty)
2. ✅ Shots (Non-Penalty)
3. ~~Shot OBV~~ → **xG** (already included)
4. ✅ PAdj Pressures
5. ~~Pass OBV~~ → **Open Play xG Assisted**
6. ✅ Open Play xG Assisted
7. ~~Dribble & Carry OBV~~ → **Successful Dribbles** + **Progressive Carries**
8. ✅ Fouls Won
9. ✅ Turnovers
10. ✅ Touches In Box
11. ✅ xG/Shot

---

### 🔷 **Striker Radar**

**Metrics Available:**
1. ✅ xG (Non-Penalty)
2. ✅ Shots (Non-Penalty)
3. ~~Shot OBV~~ → **xG** (already included)
4. ~~Pass OBV~~ → **Open Play xG Assisted**
5. ✅ Open Play xG Assisted
6. ✅ PAdj Pressures
7. ✅ Aerial Wins
8. ✅ Turnovers
9. ~~Dribble & Carry OBV~~ → **Successful Dribbles** + **Progressive Carries**
10. ✅ Touches In Box
11. ✅ xG/Shot

---

## Possession Adjustment Formula

**Purpose:** Normalize defensive metrics for teams with different possession levels

**Formula:**
```
PAdj Metric = Raw Count × (100 / Team Possession %)
```

**Example:**
- Team A has 40% possession, makes 15 tackles
- Team B has 60% possession, makes 15 tackles
- PAdj Tackles:
  - Team A: 15 × (100 / 40) = **37.5**
  - Team B: 15 × (100 / 60) = **25.0**

**Interpretation:** Team A's 15 tackles are more impressive because they had less time out of possession.

**Apply to:**
- Tackles & Interceptions
- Pressures
- Clearances
- Blocks (optional)

---

## Next Steps

1. **Create modular query functions** in `fifa_metrics_bq.py`:
   - `get_player_radar_metrics_by_position(player, team, position, competition)`
   - Individual metric functions for reusability

2. **Create radar visualization function** in `fifa_visualizations_bq.py`:
   - `create_player_radar_by_position(client, player, team, position, competition)`
   - Use `mplsoccer.Radar` with position-specific templates

3. **Add position detection logic**:
   - Query player's most common position from `position` field
   - Default to generic radar if position is unknown

4. **Create percentile-based normalization**:
   - Calculate percentiles across all players in same position
   - Use for radar scaling (0-100 scale)

5. **Testing**:
   - Validate queries with known players (Messi, Ronaldo, Van Dijk, etc.)
   - Compare with existing team radar metrics for consistency

---

## Summary

✅ **Feasible:** 17 out of 29 StatsBomb 2023 metrics
⚠️ **Partial Support:** 2 metrics (goalkeeper-specific)
❌ **Not Feasible:** 10 metrics (all OBV-based + specialized goalkeeper metrics)

**Recommendation:** Focus on **outfield player radars** (Centre Backs through Strikers) where we have strong data coverage. Skip goalkeeper radars due to missing specialized metrics.
