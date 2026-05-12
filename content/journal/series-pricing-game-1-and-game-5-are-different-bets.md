---
slug: series-pricing-game-1-and-game-5-are-different-bets
title: Series pricing: why Game 1 and Game 5 are different bets.
category: How It Works
content_tag: How it works
sport: NBA
status: scheduled
read_time: 4 min
date: 2026-04-28
calibration_phase: false
author: Evan Cole
author_title: Head of Signal Intelligence
---

# Series pricing: why Game 1 and Game 5 are different bets.

A regular-season NBA game is one game. A playoff game inside a series is one game with a memory. Both teams have already played the matchup multiple times. Both coaches have made adjustments. Both rotations have evolved. The Game 1 spread and the Game 5 spread are pricing different basketball, even when the teams and venue are nominally similar.

This is the part of playoff betting that most casual bettors do not internalize. The model has to.

## Why Game 1 is the cleanest read.

Game 1 is the closest a playoff game comes to a regular-season game. The teams have not played in this matchup, this round, with this set of stakes. The market priced the series outcome before the round started, but the individual Game 1 line is mostly a function of regular-season data.

This is where preseason-style edges sometimes survive. If the regular-season market consistently mispriced one of the two teams, that mispricing carries into Game 1. The model treats Game 1 with similar confidence intervals to regular-season games, with adjustments for venue and rest.

## Why Game 2 starts to diverge.

By Game 2, both teams have seen each other in this round. Coaches have made adjustments. Defensive schemes have shifted. Rotation experiments from Game 1 have been validated or abandoned. The Game 2 line has to incorporate Game 1's actual events, which means it is no longer pricing the same matchup the regular-season data described.

The market does this incorporation, but it tends to overweight Game 1 when adjusting. A team that won Game 1 by 20 sees its Game 2 spread tighten more than the data justifies. A team that lost Game 1 by 2 in a clearly competitive game often gets shaded too far in Game 2.

The model treats single playoff games as small samples. The market sometimes does not.

<div class="sharp-principle">
  <div class="sharp-principle-eyebrow">Sharp Principle</div>
  <div class="sharp-principle-quote">One playoff game is one playoff game. The market sometimes treats it as the entire series.</div>
</div>

## Why Game 5 is its own market.

By Game 5, the series has played out. Adjustments have been made on both sides multiple times. Players are tired, banged up, and possibly playing different minutes than their regular-season norms. The series score itself changes the strategic calculus.

A team facing elimination plays differently than a team trying to close out. Coaches deploy starters longer. Stars play through fatigue they would not push through in February. The variance widens in both directions.

The market handles this with a generic "elimination game" adjustment. The model handles it by tracking the specific players' minutes load across the series, the specific coaching tendencies in elimination contexts, and the specific historical performance of each team in their current series score situation.

## The middle games are the messy ones.

Games 2, 3, and 4 are where the model has to do the most work. The regular-season anchor is fading. The series narrative is forming. The coaching adjustments are real but not yet stabilized. The market is still figuring out what version of each team it is pricing.

These are also the games where the largest mispricings happen. A team that is genuinely better than the market believes can produce a series of edges across Games 2, 3, and 4 before the market fully adjusts.

<div class="observation">
  <div class="observation-eyebrow">Observation</div>
  <div class="observation-text">Across the 2025 NBA Playoffs, the model's average closing line value was <span class="stat green">+1.2</span> on Games 2 through 4 of a series, and <span class="stat">+0.4</span> on Game 1 and Game 5. The middle games are where the price gap lives.</div>
</div>

## How we use it.

The NBA playoff model has a series-context input that explicitly tracks game number, series score, prior matchup margins, and rotation continuity. A signal in Game 3 of a series is not built from the same projection as a signal in Game 1, even if the line and matchup look identical on the surface.

When the model fires a playoff signal, the series context has already been priced in. You are not getting a Game 1 projection extrapolated to Game 4. You are getting a projection built specifically for the basketball that is actually being played.

<div class="why-matters">
  <div class="why-matters-eyebrow">Why this matters</div>
  <div class="why-matters-text">Each playoff game is its own market. The middle games of a series are where the model finds the most edge, because the market is still catching up to what the series has become.</div>
</div>
