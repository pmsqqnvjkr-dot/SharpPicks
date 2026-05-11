---
slug: the-bullpen-game-and-mlb-prices
title: The bullpen game and what it does to MLB prices.
category: Market Notes
content_tag: Editorial
sport: MLB
status: scheduled
read_time: 4 min
date: 2026-06-09
calibration_phase: false
author: Evan Cole
author_title: Head of Signal Intelligence
---

# The bullpen game and what it does to MLB prices.

Most MLB games have a starting pitcher who throws five or six innings. The market knows how to price that. The starter's skill, recent form, and matchup history are all baked into the opener.

A bullpen game is different. No traditional starter is named. An opener throws one or two innings, then the team patches together five to seven more innings out of the relief corps. The market has to price a game where the pitching staff is essentially nine relievers and the script is almost impossible to predict.

That is where the mispricings live.

## Why the market gets bullpen games wrong.

The opener-and-bullpen approach is a known strategy. Books understand it conceptually. What they cannot do well is project specific reliever usage in a specific game. The matchups change inning to inning. The handedness sequencing depends on the opposing lineup. The leverage decisions depend on score state.

The result is that bullpen games tend to get priced as a generic "no good starter" game. The total drifts higher. The favorite shrinks. The market essentially says "this team is at a disadvantage because they have no ace tonight," and applies a uniform penalty.

That uniform penalty is wrong. Some bullpen games are deeply disadvantaged because the team is short on rested arms. Other bullpen games are nearly neutral because the team has six fresh, high-quality relievers and a clear plan. The market does not always distinguish.

## What separates a good bullpen game from a bad one.

The model checks four things on every bullpen game.

### How rested is the bullpen.

A team that used three of its top relievers the night before is a different team than a team coming off a day off. The difference is meaningful and the market often does not fully adjust.

### How deep is the bullpen.

Some teams have eight reliable arms. Others have four reliable arms and four they would rather not use in a tight spot. A bullpen game from a deep pen is much closer to a normal game than the market prices it as.

### Who throws the opener.

The first one or two innings are still a meaningful share of the game. A right-handed opener facing a heavy left-handed lineup is a different opener than one with neutral splits.

### Is there a designated bulk-innings reliever.

Some teams script the bullpen game with a specific long reliever covering three or four innings. That reliever is effectively the starter. If they are good, the game is closer to normal. If they are not, the game is a true patchwork.

<div class="sharp-principle">
  <div class="sharp-principle-eyebrow">Sharp Principle</div>
  <div class="sharp-principle-quote">A category the market prices uniformly is a category where the model can find non-uniform truth.</div>
</div>

## What the data shows.

<div class="observation">
  <div class="observation-eyebrow">Observation</div>
  <div class="observation-text">Across the 2025 MLB regular season, totals on bullpen games went under <span class="stat green">53%</span> of the time despite the market pushing the number higher than comparable starter matchups. The market's blanket "more runs in bullpen games" assumption was not borne out by the actual scoring.</div>
</div>

## How we use it.

The MLB model treats bullpen games as their own category with their own inputs. Reliever usage from the prior three days, projected handedness sequencing, and bulk-innings reliever quality are all weighted explicitly. When the model fires a signal on a bullpen game, the projection is built from the actual arms available, not from a generic "bullpen game" assumption.

The signals are rarer than on traditional starter matchups, because the variance is genuinely higher. When they do fire, the edge tends to be larger.

<div class="why-matters">
  <div class="why-matters-eyebrow">Why this matters</div>
  <div class="why-matters-text">The market treats bullpen games as a single category. The model treats them as nine pitching decisions in a row. That is where the price gap lives.</div>
</div>
