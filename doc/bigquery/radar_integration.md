# StatsBomb Radar Integration Plan - Using Existing Code

**Date:** October 20, 2025
**Purpose:** Map StatsBomb 2023 radar metrics to our EXISTING codebase to avoid duplicate API calls

---

## Key Finding: We Already Calculate 80% of What We Need!

Our existing functions in `fifa_metrics_bq.py` already calculate most radar metrics. We just need to:
1. **Extract** the right metrics from existing functions
2. **Add** a few missing calculations (PAdj metrics, aerial wins, turnovers)
3. **Create** position-specific radar helper functions

---

## Existing Metrics Coverage

### ✅ From `analyze_player_metrics()` - Already Available

| Radar Metric | Current Metric | Location |
|--------------|----------------|----------|
| **xG (Non-Penalty)** | ✅ `total_xg` (all shots) | Line 668 |
| **Shots (Non-Penalty)** | ✅ `shots` | Line 665 |
| **xG/Shot** | ⚠️ Need to calculate: `total_xg / shots` | Derived |
| **Aerial Wins** | ❌ Not calculated | **NEED TO ADD** |
| **Aerial Win %** | ❌ Not calculated | **NEED TO ADD** |
| **Turnovers** | ⚠️ Partial: `miscontrols_errors` | Line 682 (missing dispossessed) |
| **Fouls Won** | ✅ `fouls_won` | Line 697 |
| **Fouls Committed** | ✅ `fouls` | Line 695 |
| **Tackles** | ✅ `tackles` | Line 685 |
| **Interceptions** | ✅ `successful_interceptions` | Line 687 |
| **Dribbles** | ✅ `successful_dribbles` | Line 680 |
| **Blocks** | ✅ `blocks` | Line 690 |
| **Clearances** | ✅ `clearances` | Line 698 |
| **Dribbled Past** | ✅ `dribbled_past` | Line 692 |

**Coverage:** 11/14 metrics (79%) ✅

---

### ✅ From `analyze_team_metrics()` - Already Available

| Radar Metric | Current Metric | Location |
|--------------|----------------|----------|
| **Deep Progressions (Passes)** | ✅ `final_3rd_passes` | `_analyze_team_metrics_consolidated()` Line 301 |
| **Deep Progressions (Carries)** | ✅ `final_3rd_carries` | Line 303 |
| **Through Ball %** | ✅ `through_ball_percentage` | `_calculate_passing_derived_metrics()` Line 428 |
| **Cross %** | ✅ `cross_percentage` | Line 426 |
| **Pass Completion %** | ✅ `pass_completion_rate` | Line 424 |
| **Under Pressure Pass %** | ✅ `under_pressure_percentage` | Line 425 |
| **Shots on Target %** | ✅ `shots_on_target_percentage` | `_calculate_shooting_derived_metrics()` Line 463 |
| **Counter Shots per Game** | ✅ `counter_shots_per_match` | Line 477 |
| **Shots Under Pressure per Game** | ✅ `shots_under_pressure_per_match` | Line 478 |
| **xG per Shot** | ✅ `xg_per_shot` | Line 467 |
| **Set Piece xG** | ✅ `avg_xG_set_piece` | Line 325 |
| **GK Pass Length** | ✅ `goalkeeper_pass_avg_length` | Line 307 |

**Coverage:** 12/12 metrics (100%) ✅

---

## Metrics We NEED TO ADD

### 1. **PAdj (Possession-Adjusted) Metrics** ❌

These are NOT calculated anywhere. Need to add:

```python
def calculate_possession_adjusted_metrics(client, player_name, team_name, competition=None):
    """
    Calculate possession-adjusted defensive metrics.
    Formula: PAdj = Raw Count × (100 / Team Possession %)
    """
    # Get team possession per match
    # Multiply tackles, interceptions, pressures, clearances by adjustment factor
    pass
```

**Required for:**
- PAdj Tackles & Interceptions
- PAdj Pressures
- PAdj Clearances

---

### 2. **Aerial Duels** ❌

Currently NOT calculated. Need to add to `analyze_player_metrics()`:

```sql
-- ADD TO EXISTING QUERY (Line 657)
-- Aerial Duels
COUNTIF(duel_type = 'Aerial Lost') as aerial_duels,
COUNTIF(duel_type = 'Aerial Lost' AND duel_outcome IN ('Won', 'Success In Play', 'Success Out')) as aerial_wins,
ROUND(SAFE_DIVIDE(
    COUNTIF(duel_type = 'Aerial Lost' AND duel_outcome IN ('Won', 'Success In Play', 'Success Out')),
    COUNTIF(duel_type = 'Aerial Lost')
) * 100, 1) as aerial_win_percentage,
```

---

### 3. **Turnovers (Complete Definition)** ⚠️

We have `miscontrols_errors` but missing "Dispossessed" and "Failed Dribbles"

```sql
-- MODIFY EXISTING LINE (Line 682)
-- OLD:
COUNTIF(type = 'Miscontrol' OR type = 'Error') as miscontrols_errors,

-- NEW:
COUNTIF(type = 'Miscontrol' OR type = 'Error') as miscontrols_errors,
COUNTIF(type = 'Dispossessed') as dispossessed,
COUNTIF(type = 'Dribble' AND dribble_outcome = 'Incomplete') as failed_dribbles,
-- Total turnovers = miscontrols + dispossessed + failed dribbles
COUNTIF(
    type IN ('Miscontrol', 'Dispossessed', 'Error')
    OR (type = 'Dribble' AND dribble_outcome = 'Incomplete')
) as turnovers,
```

---

### 4. **Open Play xG Assisted** ⚠️

We have `assists` but not specifically "open play xG assisted"

```sql
-- ADD TO EXISTING QUERY
-- Open Play xG Assisted (requires JOIN with shot events)
SUM(CASE
    WHEN pass_shot_assist = TRUE
     AND play_pattern NOT IN ('From Corner', 'From Free Kick')
    THEN (SELECT shot_statsbomb_xg FROM events e2
          WHERE e2.id = e.pass_assisted_shot_id LIMIT 1)
    ELSE 0.0
END) as open_play_xg_assisted,
```

**NOTE:** This requires a subquery or JOIN, which is complex. **Alternative:** Calculate in Python after query.

---

### 5. **Touches In Box** ⚠️

Need to add spatial filter:

```sql
-- ADD TO EXISTING QUERY
-- Touches in Opposition Box (x >= 102, y between 18 and 62)
COUNTIF(
    x >= 102 AND x <= 120
    AND y >= 18 AND y <= 62
    AND type IN (
        'Pass', 'Ball Receipt*', 'Carry', 'Shot', 'Dribble',
        'Duel', 'Clearance', 'Miscontrol', 'Dispossessed'
    )
) as touches_in_box,
```

---

### 6. **Tackle vs Dribbled Past %** ⚠️

We have both `tackles` and `dribbled_past` separately. Need derived metric:

```python
# In _calculate_player_radar_metrics() helper
tackle_dribbled_past_pct = (tackles / (tackles + dribbled_past)) * 100
```

---

### 7. **Being Pressured Change in Pass %** ⚠️

We have `pass_completion_rate` and `under_pressure_percentage`, but need:

```sql
-- ADD TO EXISTING QUERY
-- Pass completion under pressure
ROUND(SAFE_DIVIDE(
    COUNTIF(type = 'Pass' AND pass_outcome IS NULL AND under_pressure = TRUE),
    COUNTIF(type = 'Pass' AND under_pressure = TRUE)
) * 100, 1) as pass_completion_under_pressure,
```

Then calculate difference:
```python
pass_pct_change = pass_completion_under_pressure - pass_completion_rate
```

---

### 8. **Blocks per Shot Faced** ⚠️

We have `blocks` but not "shots faced". Need to query opponent shots in same matches.

```sql
-- Separate query for shots faced (team-level)
WITH team_matches AS (
    SELECT DISTINCT match_id FROM events WHERE team = @team_name
)
SELECT COUNTIF(type = 'Shot') as shots_faced
FROM events
WHERE match_id IN (SELECT match_id FROM team_matches)
  AND team != @team_name
```

Then: `blocks_per_shot = blocks / shots_faced`

---

## Proposed Integration Approach

### **Option 1: Extend Existing Functions (RECOMMENDED)**

Modify `analyze_player_metrics()` to include radar-specific metrics:

```python
def analyze_player_metrics(client, player_name, team_name=None, competition=None,
                          include_radar_metrics=False):
    """
    Enhanced version with optional radar metrics.

    If include_radar_metrics=True, also calculates:
    - Aerial wins & aerial win %
    - Complete turnovers (miscontrols + dispossessed + failed dribbles)
    - Touches in box
    - Open play xG assisted
    - Pass completion under pressure
    - Possession-adjusted metrics (if team context available)
    """
    # ... existing query ...

    if include_radar_metrics:
        # Add radar-specific calculations to SQL query
        pass
```

**Pros:**
- Single function call
- Reuses existing caching
- No duplicate API calls

**Cons:**
- Makes query slightly more complex
- Not all radar metrics needed for all use cases

---

### **Option 2: Create Separate Radar Metrics Function**

Create new function that leverages existing calculations:

```python
def get_player_radar_metrics(client, player_name, team_name, position, competition=None):
    """
    Get position-specific radar metrics for a player.

    Internally calls:
    1. analyze_player_metrics() for base metrics
    2. Calculates missing radar-specific metrics (aerial, PAdj, etc.)
    3. Returns position-specific subset
    """
    # Get base metrics from existing function
    base_metrics = analyze_player_metrics(client, player_name, team_name, competition)

    # Calculate missing metrics
    aerial_metrics = _get_aerial_metrics(client, player_name, team_name, competition)
    padj_metrics = _get_possession_adjusted_metrics(client, player_name, team_name, competition)
    spatial_metrics = _get_spatial_metrics(client, player_name, team_name, competition)

    # Combine and filter by position
    all_metrics = {**base_metrics, **aerial_metrics, **padj_metrics, **spatial_metrics}

    return _filter_metrics_by_position(all_metrics, position)
```

**Pros:**
- Clean separation of concerns
- Easy to add new radar templates
- Existing functions unchanged

**Cons:**
- Multiple function calls
- Potentially more API calls (though cached)

---

## Recommended Implementation Plan

### **Phase 1: Extend `analyze_player_metrics()`** (1-2 hours)

1. Add 5-10 lines to the SQL query for missing metrics:
   - Aerial duels (2 lines)
   - Complete turnovers (4 lines)
   - Touches in box (1 line)
   - Pass completion under pressure (2 lines)

2. Add optional `include_radar_metrics=True` parameter

**File:** `fifa_metrics_bq.py` (Lines 657-717)

---

### **Phase 2: Create Helper Functions** (1 hour)

Create position-specific radar extractors:

```python
# Add to fifa_metrics_bq.py

def get_striker_radar_metrics(player_metrics):
    """Extract radar metrics for striker position."""
    return {
        'xG': player_metrics['total_xg'],
        'Shots': player_metrics['shots'],
        'xG/Shot': player_metrics['total_xg'] / max(player_metrics['shots'], 1),
        'Open Play xG Assisted': player_metrics.get('open_play_xg_assisted', 0),
        'Aerial Wins': player_metrics.get('aerial_wins', 0),
        'Turnovers': player_metrics.get('turnovers', 0),
        'Touches In Box': player_metrics.get('touches_in_box', 0),
        # ... etc
    }

def get_centre_back_radar_metrics(player_metrics):
    """Extract radar metrics for centre back position."""
    return {
        'Aerial Win %': player_metrics.get('aerial_win_percentage', 0),
        'Aerial Wins': player_metrics.get('aerial_wins', 0),
        'Pass Completion %': player_metrics['pass_completion_rate'],
        # ... etc
    }

# Similar for: full_back, midfielder, attacking_mid, winger
```

---

### **Phase 3: Add PAdj Metrics** (2 hours)

Create separate function for possession-adjusted metrics:

```python
@st.cache_data(ttl=600)
def get_possession_adjusted_metrics(_client, player_name, team_name, competition=None):
    """
    Calculate possession-adjusted defensive metrics.

    Returns:
    - padj_tackles_interceptions
    - padj_pressures
    - padj_clearances
    """
    # Query 1: Get player's raw defensive actions per match
    # Query 2: Get team possession % per match
    # Calculate: raw_count × (100 / possession_pct)
    pass
```

**File:** `fifa_metrics_bq.py`

---

### **Phase 4: Create Radar Visualization** (1-2 hours)

Use existing `create_team_radar_chart()` as template:

```python
def create_player_radar_chart(client, player_name, team_name, position,
                              competition=None, font_properties=None):
    """
    Create position-specific radar chart for player.

    Automatically selects correct metrics based on position.
    """
    # Get all player metrics
    player_metrics = analyze_player_metrics(
        client, player_name, team_name, competition,
        include_radar_metrics=True
    )

    # Get position-specific radar values
    if position in ['Striker', 'Centre-Forward']:
        radar_values = get_striker_radar_metrics(player_metrics)
    elif position in ['Centre Back', 'Center Back']:
        radar_values = get_centre_back_radar_metrics(player_metrics)
    # ... etc

    # Calculate percentile boundaries (across all players in position)
    low, high = calculate_radar_boundaries(client, position, competition)

    # Create radar using mplsoccer.Radar
    return _create_radar_visualization(radar_values, low, high, ...)
```

**File:** `fifa_visualizations_bq.py`

---

## Metrics Summary Table

| Metric | Status | Source | Action Needed |
|--------|--------|--------|---------------|
| xG (Non-Penalty) | ✅ Ready | `analyze_player_metrics()` | None |
| Shots | ✅ Ready | `analyze_player_metrics()` | None |
| xG/Shot | ✅ Ready | Derived from above | Calculate in Python |
| Goals | ✅ Ready | `analyze_player_metrics()` | None |
| Assists | ✅ Ready | `analyze_player_metrics()` | None |
| Open Play xG Assisted | ⚠️ Complex | **Need to add** | Add JOIN or subquery |
| Shots on Target % | ✅ Ready | `analyze_team_metrics()` | None |
| Through Ball % | ✅ Ready | `analyze_team_metrics()` | None |
| Cross % | ✅ Ready | `analyze_team_metrics()` | None |
| Pass Completion % | ✅ Ready | `analyze_player_metrics()` | None |
| Pass Completion Under Pressure | ⚠️ Missing | **Need to add** | Add 2 lines to SQL |
| Being Pressured Change in Pass % | ⚠️ Missing | **Need to add** | Derive from above |
| Deep Progressions | ✅ Ready | `analyze_team_metrics()` | None |
| Dribbles (Successful) | ✅ Ready | `analyze_player_metrics()` | None |
| Tackles | ✅ Ready | `analyze_player_metrics()` | None |
| Interceptions | ✅ Ready | `analyze_player_metrics()` | None |
| PAdj Tackles & Interceptions | ❌ Missing | **Need to add** | New function |
| PAdj Pressures | ❌ Missing | **Need to add** | New function |
| PAdj Clearances | ❌ Missing | **Need to add** | New function |
| Clearances | ✅ Ready | `analyze_player_metrics()` | None |
| Blocks | ✅ Ready | `analyze_player_metrics()` | None |
| Blocks/Shot | ⚠️ Missing | **Need to add** | Query shots faced |
| Aerial Wins | ❌ Missing | **Need to add** | Add 2 lines to SQL |
| Aerial Win % | ❌ Missing | **Need to add** | Add 2 lines to SQL |
| Turnovers (Complete) | ⚠️ Partial | **Need to add** | Add 3 lines to SQL |
| Fouls Won | ✅ Ready | `analyze_player_metrics()` | None |
| Fouls Committed | ✅ Ready | `analyze_player_metrics()` | None |
| Touches In Box | ❌ Missing | **Need to add** | Add 1 line to SQL |
| Tackle/Dribbled Past % | ⚠️ Missing | **Need to add** | Derive from existing |
| Dribbled Past | ✅ Ready | `analyze_player_metrics()` | None |

**Summary:**
- ✅ **Ready:** 18 metrics (62%)
- ⚠️ **Easy to add:** 7 metrics (24%) - just SQL modifications
- ❌ **Need new function:** 4 metrics (14%) - PAdj calculations

---

## Estimated Work

### Total Time: 5-7 hours

1. **SQL Query Modifications** (2 hours)
   - Add 10-15 lines to `analyze_player_metrics()` query
   - Add `include_radar_metrics` parameter

2. **PAdj Metrics Function** (2 hours)
   - Create `get_possession_adjusted_metrics()`
   - Test with various teams/players

3. **Position-Specific Helpers** (1 hour)
   - Create 6 position-specific extractor functions
   - Map StatsBomb metrics to our metrics

4. **Radar Visualization** (1-2 hours)
   - Create `create_player_radar_chart()`
   - Reuse logic from `create_team_radar_chart()`
   - Add percentile calculations

5. **Testing & Integration** (1 hour)
   - Test with known players
   - Integrate into dashboard
   - Add to Player Analysis tab

---

## Benefits of This Approach

✅ **Reuses 80% of existing code** - No duplicate queries
✅ **Leverages existing caching** - Fast performance
✅ **Minimal new code** - Just fill in gaps
✅ **Clean architecture** - Optional radar metrics don't bloat base functions
✅ **Easy to test** - Can test new metrics independently
✅ **Backward compatible** - Existing dashboard continues to work

---

## Next Steps

1. **Review this plan** - Confirm approach
2. **Prioritize metrics** - Which positions first?
3. **Start with Phase 1** - Extend `analyze_player_metrics()`
4. **Test incrementally** - Validate each addition
5. **Add to dashboard** - Integrate into Player Analysis tab

---

## Code Changes Required

### File: `fifa_metrics_bq.py`

**Line 657-717:** Modify `analyze_player_metrics()` query:

```sql
-- ADD AFTER LINE 700 (cards):

-- RADAR-SPECIFIC METRICS (only if include_radar_metrics=True)
-- Aerial Duels
COUNTIF(duel_type = 'Aerial Lost') as aerial_duels,
COUNTIF(duel_type = 'Aerial Lost' AND duel_outcome IN ('Won', 'Success In Play', 'Success Out')) as aerial_wins,

-- Complete Turnovers
COUNTIF(type = 'Dispossessed') as dispossessed,
COUNTIF(type = 'Dribble' AND dribble_outcome = 'Incomplete') as failed_dribbles,
COUNTIF(
    type IN ('Miscontrol', 'Dispossessed', 'Error')
    OR (type = 'Dribble' AND dribble_outcome = 'Incomplete')
) as turnovers,

-- Touches In Box
COUNTIF(
    x >= 102 AND x <= 120
    AND y >= 18 AND y <= 62
    AND type IN ('Pass', 'Ball Receipt*', 'Carry', 'Shot', 'Dribble', 'Duel')
) as touches_in_box,

-- Pass Completion Under Pressure
COUNTIF(type = 'Pass' AND pass_outcome IS NULL AND under_pressure = TRUE) as passes_under_pressure_completed,
COUNTIF(type = 'Pass' AND under_pressure = TRUE) as passes_under_pressure_total,
ROUND(SAFE_DIVIDE(
    COUNTIF(type = 'Pass' AND pass_outcome IS NULL AND under_pressure = TRUE),
    COUNTIF(type = 'Pass' AND under_pressure = TRUE)
) * 100, 1) as pass_completion_under_pressure,

-- DERIVED METRICS (calculated in SQL)
ROUND(SAFE_DIVIDE(
    COUNTIF(duel_type = 'Aerial Lost' AND duel_outcome IN ('Won', 'Success In Play', 'Success Out')),
    COUNTIF(duel_type = 'Aerial Lost')
) * 100, 1) as aerial_win_percentage,
```

**NEW FUNCTION:** Add after `analyze_player_metrics()`

```python
def get_possession_adjusted_metrics(client, player_name, team_name, competition=None):
    """Calculate possession-adjusted defensive metrics."""
    # Implementation here
    pass

def get_striker_radar_metrics(player_metrics):
    """Extract striker radar metrics from player metrics dict."""
    # Implementation here
    pass

# ... similar for other positions
```

---

This integration approach is **much more efficient** than writing new queries because we're building on top of what we already have! 🚀
