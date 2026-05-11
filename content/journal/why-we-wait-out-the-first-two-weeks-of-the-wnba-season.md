---
slug: why-we-wait-out-the-first-two-weeks-of-the-wnba-season
title: Why we wait out the first two weeks of the WNBA season.
category: Discipline
content_tag: Field Guide
sport: WNBA
status: scheduled
read_time: 3 min
date: 2026-05-26
calibration_phase: true
author: Evan Cole
author_title: Head of Signal Intelligence
---

# Why we wait out the first two weeks of the WNBA season.

The WNBA season starts. The slate is fresh. Twelve teams have new rotations, new coaches in some cases, and roster turnover from the offseason. The market has to price all of it from scratch.

This is exactly the moment when the model fires the fewest signals. That is by design.

## What is missing in May.

Every preseason model carries assumptions. Some of those assumptions will be wrong. A team that lost two starters and added three rookies is not the team it was last year. A coach in their first season has not yet shown how they rotate the bench. A player coming back from an offseason injury is not the same player they were before.

The only reliable way to update those assumptions is to watch teams play games. Not preseason games. Real ones, against real opponents, with real outcomes. The first two weeks of the season are the model's eyes adjusting to the dark.

## What the market does instead.

The market does not wait. Books open lines on opening night and take action on every game. The opening lines are often anchored heavily on last season's data, with adjustments for known roster moves. Those anchors are sometimes right and sometimes badly wrong. The variance is wider than at any other point in the season.

In theory this is opportunity. A model could find edges by being faster than the market to update on early-season information. In practice, that strategy gets crushed by sample size. Three games of evidence is not enough to override two years of historical data, no matter how compelling the early signal looks.

<div class="sharp-principle">
  <div class="sharp-principle-eyebrow">Sharp Principle</div>
  <div class="sharp-principle-quote">A small sample is loud. A small sample is also wrong.</div>
</div>

## The discipline cost.

Waiting out the first two weeks costs the model some real edges. There are games in mid-May where the model would have been right and the market would have been wrong. Those edges are not free to collect. They come with a much higher rate of edges where the model would have been wrong because it had not yet seen the team play.

Across an entire season, the cost of patience is small. The cost of impatience is large.

<div class="observation">
  <div class="observation-eyebrow">Observation</div>
  <div class="observation-text">In our 2025 shadow run, signals fired in the first 14 days of the season had a closing line value of <span class="stat negative">-0.3</span>. Signals fired after day 14 had a CLV of <span class="stat green">+1.6</span>. Same model, same threshold, dramatically different signal quality.</div>
</div>

## How we use it.

The WNBA model runs in a quieter mode for the first two weeks of the regular season. The discipline filter is set tighter, the edge threshold is raised, and the model defaults to passing on close calls. By around game 8 or 9 for most teams, enough information has accumulated for the filter to relax to its normal setting.

If you see fewer signals in the first two weeks, that is the model doing exactly what it is supposed to do.

<div class="why-matters">
  <div class="why-matters-eyebrow">Why this matters</div>
  <div class="why-matters-text">A quiet start is not a broken model. It is a model that knows what it does not know yet.</div>
</div>
