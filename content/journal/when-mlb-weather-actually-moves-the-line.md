---
slug: when-mlb-weather-actually-moves-the-line
title: When MLB weather actually moves the line.
category: Market Notes
content_tag: Editorial
sport: MLB
status: scheduled
read_time: 4 min
date: 2026-06-16
calibration_phase: false
author: Evan Cole
author_title: Head of Signal Intelligence
---

# When MLB weather actually moves the line.

Every MLB total carries a weather assumption. The market pulls the forecast, applies a generic adjustment for temperature and wind, and prints a number. Most of the time this works. Sometimes it does not, and the gap between the generic adjustment and the actual baseball that gets played is where the model finds edge.

The mistake is assuming every weather report is a betting input. Most are not. The signal lives in a narrow band of conditions.

## Temperature is mostly priced.

Books have a long history of pricing temperature. A warm-air park plays slightly higher than a cold-air park at the same elevation. The market knows this. A 90-degree game in a hitter's park gets a roughly correct total adjustment.

What the market handles worse is the edge case. A 50-degree game in May at Wrigley with the wind from the lake plays nothing like the season-long Wrigley baseline. A 100-degree afternoon game in Texas with no shade plays differently than a 100-degree night game at the same park. The generic temperature adjustment does not capture these.

The model checks temperature against the specific park, the specific time of day, and the specific seasonal baseline for that combination. That is what produces a real adjustment versus a generic one.

## Wind is the variable that actually moves games.

Wind direction and speed have a much larger effect on offense than temperature does, and the market prices wind less accurately than it prices temperature. The reasons are mechanical. Wind reports change closer to game time. The exact direction relative to the field varies by stadium. The interaction between wind and ball flight is not linear.

A 15-mph wind blowing out at Wrigley is a different baseball game than a 15-mph wind blowing in at Wrigley. The market knows this. A 15-mph wind blowing across the field, neither in nor out, is closer to neutral than the simple wind speed suggests. The market sometimes prices it as if it matters more than it does.

<div class="sharp-principle">
  <div class="sharp-principle-eyebrow">Sharp Principle</div>
  <div class="sharp-principle-quote">Wind direction matters more than wind speed. Both are priced less efficiently than temperature.</div>
</div>

## When weather is not a signal.

Most weather reports do not produce a betting input. A 72-degree game with light variable wind at a neutral park is a non-event for the total. Treating every forecast as a signal is how you talk yourself into bad bets that the market has already priced correctly.

The model only treats weather as an active input when three conditions align: the park has a known wind sensitivity, the wind speed is above 10 mph, and the direction is clearly in or out of the field rather than across. Below those thresholds, weather sits in the background, included in the projection but not given extra weight.

<div class="observation">
  <div class="observation-eyebrow">Observation</div>
  <div class="observation-text">Across the 2025 MLB regular season, games where the wind was 12+ mph blowing out at a hitter-friendly park went over the total <span class="stat green">56%</span> of the time. Games with the same temperature and matchup but neutral or low wind hit the over <span class="stat">49%</span> of the time. The 7-point gap is entirely wind.</div>
</div>

## How we use it.

The MLB model has a weather input that activates only when the conditions cross specified thresholds. The default behavior is to treat weather as included in the baseline projection. The active behavior is to adjust the projection upward or downward based on the specific park-wind interaction. When the model fires a total signal that is partially driven by weather, the disclosure on the signal card identifies it as a weather-influenced read.

What the model will not do is fire a signal because the wind is blowing. The wind has to clear the threshold and combine with other factors. Weather alone is rarely enough.

<div class="why-matters">
  <div class="why-matters-eyebrow">Why this matters</div>
  <div class="why-matters-text">Most weather reports are not betting inputs. The narrow band of conditions where weather genuinely moves a price is small and specific. Treating every forecast as a signal is how generic edges get talked into existence.</div>
</div>
