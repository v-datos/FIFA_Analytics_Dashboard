Excellent! I've reviewed both dashboard scripts. Let me create a comprehensive plan to enhance each tab of our football analytics dashboard, incorporating the best visualizations and metrics from the Copa America reference dashboard.

## 📋 Enhancement Plan by Tab

### **Tab 1: 🏆 Competition Analysis**

**Current State:** Basic metrics and top scorers table

**Enhancements to Add:**

1. **xG Timeline Chart (Plotly)**
   - Average xG for/against across all teams in competition
   - Similar to `create_xg_timeline()` from reference

2. **Competition-wide Heatmaps**
   - Pressure events heatmap (aggregated across all teams)
   - Shot locations heatmap
   - Based on `plot_pressure_heatmap()` and shot map concepts

3. **Statistical Distributions**
   - xG distribution across all teams (using `plot_multiple_team_xg_distributions()`)
   - Pass completion rate comparison
   - Goalkeeper pass length comparison

4. **Additional Metrics Grid**
   - Total pressure events
   - Average shots per match
   - Average pass completion %
   - Set piece goals vs open play

**New Visualizations:**
- Plotly line chart for competition trends over time
- Seaborn violin plots for metric distributions
- mplsoccer pitch visualizations for aggregate shot/pass maps

---

### **Tab 2: ⚔️ Match Analysis**

**Current State:** Match selection, basic team stats side-by-side

**Enhancements to Add:**

1. **Pass Network Visualization**
   - Implement `plot_match_passes()` showing completed passes by half
   - Arrow maps showing pass direction and frequency

2. **Shot Maps Comparison**
   - Side-by-side shot maps for both teams (using `plot_team_shot_map()` concept)
   - Size = xG, color = outcome (goal vs no goal)
   - mplsoccer pitch with scatter plots

3. **Touch Heatmap Comparison**
   - Implement `plot_team_touch_comparison()` 
   - Show where each team had possession on the pitch

4. **Progressive Actions**
   - Passes into final third
   - Carries into final third
   - Based on `plot_progression_against_team()`

5. **Match Timeline**
   - xG accumulation over time during the match
   - Key events markers (goals, cards, substitutions)

**New Metrics:**
- Expected goals timeline by minute
- Possession % by pitch zone
- Defensive actions (blocks, clearances, interceptions) per team
- Pass accuracy by pitch third

---

### **Tab 3: 🛡️ Team Analysis**

**Current State:** Team selector, basic stats, roster table

**Enhancements to Add:**

1. **Team Performance Radar Chart**
   - Implement `create_team_radar_chart()` with metrics:
     - Non-Penalty xG
     - Shots on Target %
     - Shots per Game
     - Counter Attacking Shots
     - Set Piece xG
     - Shots Under Pressure
     - Through ball %
     - GK Pass Length
     - Cross %

2. **Shot Map with xG**
   - Based on `create_shot_map()` from reference
   - mplsoccer pitch showing all team shots
   - Size proportional to xG value
   - Goals vs non-goals differentiated

3. **Attacking Passes Visualization**
   - Implement `plot_attacking_passes()`
   - 4-panel view: Crosses, Cutbacks, Switches, Through balls
   - Arrow maps on vertical pitches

4. **Distribution Plots (2x2 grid)**
   - xG Distribution (`plot_xg_distribution()`)
   - xG per Shot Distribution (`plot_xg_per_shot_distribution()`)
   - GK Pass Length Distribution (`plot_gk_pass_length_distribution()`)
   - xG by Shot Type (`plot_shot_xg_by_type()`)

5. **Passing Analysis**
   - Player passing under pressure scatter plot (`plot_player_passing_under_pressure()`)
   - Shows completion rate vs under-pressure completion rate

6. **Defensive Metrics Section**
   - Shots against visualization (`plot_shots_against()`)
   - Progression against team (`plot_progression_against_team()`)
   - Pressure heatmap (`plot_pressure_heatmap()`)

**Additional Stats:**
- Matches played
- Goals for/against
- xG for/against
- Pass completion overall and under pressure
- Shot accuracy and conversion rate
- Defensive actions (blocks, clearances, interceptions)
- Cards received

---

### **Tab 4: 👤 Player Analysis**

**Current State:** Player search, basic stats, match history

**Enhancements to Add:**

1. **Player Performance Radar**
   - Customized radar for player position
   - Forward radar: Goals, Shots, xG, Dribbles, Pass completion
   - Midfielder radar: Passes, Key passes, Tackles, Interceptions
   - Defender radar: Tackles, Clearances, Blocks, Pass completion

2. **Shot Map (Individual)**
   - Similar to team shot map but for individual player
   - Show xG values and outcomes

3. **Pass Map**
   - Individual player's pass completion
   - Pass directions and lengths
   - Successful vs unsuccessful

4. **Heat Map**
   - Player touch locations on pitch
   - Where player is most active

5. **Performance Over Time**
   - Player stats progression across matches
   - Line charts for goals, assists, xG per match

6. **Comparison Mode**
   - Select 2 players to compare side-by-side
   - Radar charts comparison
   - Stats table comparison

**Additional Metrics:**
- Dribbles completed
- Progressive passes/carries
- Defensive actions per 90
- Minutes played
- Goals per 90, Assists per 90
- xG per shot

---

### **NEW Tab 5: 📊 Advanced Analytics** (Optional)

**Purpose:** Deep-dive statistical analysis

**Content:**

1. **Team Comparison Tool**
   - Select multiple teams
   - Radar chart overlays
   - Statistical comparisons
   - Based on Tab 5 from reference dashboard

2. **Pressure Analysis**
   - Pressure events comparison (`plot_pressure_events()`)
   - Team pressure passing comparison (`plot_team_pressure_passing_comparison()`)

3. **Playing Style Clusters**
   - Scatter plots showing team styles
   - E.g., Pass completion % vs Through ball %
   - Direct play vs possession-based

4. **Set Piece Analysis**
   - Corner success rates
   - Free kick xG
   - Set piece goals by team

---

## 🎨 Visual Design Consistency

**To implement across all tabs:**

1. **Color Scheme**
   - Primary: `#1f77b4` (blue)
   - Secondary: `#ff7f0e` (orange)
   - Success: `#2ca02c` (green)
   - Danger: `#d62728` (red)
   - Neutral: `#7f7f7f` (gray)

2. **Font Usage**
   - All titles: `font_play_bold`
   - All labels: `font_play`
   - Consistent font sizes: Title (20-24), Subtitle (16-18), Labels (14-16)

3. **Pitch Visualizations**
   - Use `mplsoccer` library consistently
   - Vertical pitches for attacking analysis
   - Horizontal pitches for full-field view
   - Consistent colors for events

4. **Chart Types**
   - **Plotly** for interactive time-series and comparisons
   - **Matplotlib/Seaborn** for distributions and heatmaps
   - **mplsoccer** for pitch-based visualizations

---

## 📝 Implementation Priority

**Phase 1 (Essential):**
1. Tab 3 (Team Analysis) - Most important for users
2. Tab 2 (Match Analysis) - High value visualizations
3. Tab 1 (Competition Analysis) - Overview improvements

**Phase 2 (Enhanced):**
4. Tab 4 (Player Analysis) - Individual deep dives
5. New Tab 5 (Advanced Analytics) - Power users

---

## 🔧 Technical Requirements

**New Libraries Needed:**
```python
from mplsoccer import Pitch, VerticalPitch, Radar
from matplotlib.font_manager import FontProperties
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.patheffects as path_effects
from matplotlib.lines import Line2D
```

---
