---
slug: why-flat-staking-beats-kelly-for-almost-everyone
title: Why flat staking beats Kelly for almost everyone.
category: Discipline
content_tag: Field Guide
sport: General
status: scheduled
read_time: 4 min
date: 2026-06-23
calibration_phase: false
author: Evan Cole
author_title: Head of Signal Intelligence
---

# Why flat staking beats Kelly for almost everyone.

The Kelly criterion is the mathematically optimal bet sizing strategy. It computes the exact stake that maximizes the long-run growth rate of your bankroll given a known edge. If you know your edge precisely, Kelly wins.

You do not know your edge precisely. Nobody does. That is the entire problem.

## What Kelly actually requires.

The Kelly formula takes two inputs. The probability that your bet wins, and the price you are getting. The price is observable. The probability is not.

Every Kelly calculation in sports betting is using an estimate of probability dressed up as a fact. If your estimate is off by 5 percent in either direction, Kelly does not just become slightly suboptimal. It becomes destructive. Overestimating your edge by half leads to a Kelly stake that is twice too large, which is the exact size that produces ruin in a long enough sample.

The math of Kelly is correct. The inputs to Kelly are wrong, and not slightly wrong. Wrong in ways that compound.

## Why flat staking does not have this problem.

Flat staking sizes every bet the same. One unit per signal. The same number whether the model projects a 2 percent edge or a 5 percent edge. The same number whether you feel confident or uncertain.

This sounds like it is leaving money on the table. The 5 percent edge bets should get more money than the 2 percent edge bets. In theory, yes. In practice, the difference between a 2 percent edge and a 5 percent edge is mostly noise inside any individual model. The model knows the bet has edge. The model does not know the exact magnitude of the edge with enough precision to size differently.

Flat staking accepts this limitation rather than pretending it does not exist.

<div class="sharp-principle">
  <div class="sharp-principle-eyebrow">Sharp Principle</div>
  <div class="sharp-principle-quote">Flat staking trades a small theoretical gain for a large practical safety margin. The trade is almost always correct.</div>
</div>

## The fractional Kelly compromise.

The standard middle ground is to bet some fraction of full Kelly. Half Kelly. Quarter Kelly. The fraction reduces the damage from overestimated edges while still scaling stakes to confidence.

This works mathematically. It does not work psychologically. The cognitive load of computing a different stake for every bet, tracking which fraction of Kelly you are using, and trusting your edge estimates enough to commit to the sizing is high. Most bettors who claim to use fractional Kelly drift toward over-sizing the bets they feel good about and under-sizing the ones they feel uncertain about. That is not Kelly. That is gut sizing with a Kelly disguise.

Flat staking removes the cognitive load entirely. Every bet is the same size. There is nothing to second-guess.

## What the model actually recommends.

The SharpPicks signal card shows two sizing recommendations. A flat stake at <span class="stat">1.5u</span> for the default, and a fractional Kelly stake that uses the model's confidence input as the multiplier. The flat stake is the default. The Kelly stake is shown for users who want to size that way and understand the risks.

The reason flat is the default is not laziness. It is that flat staking is what the data actually supports for the typical user with a typical bankroll using a typical model.

<div class="observation">
  <div class="observation-eyebrow">Observation</div>
  <div class="observation-text">In a simulated 200-pick season at our model's historical edge rate, flat staking produced lower variance than quarter-Kelly while generating <span class="stat">94%</span> of the long-run return. The flat-stake bettor finished within 5 percent of the Kelly bettor in expected value, with far less month-to-month swing.</div>
</div>

## When Kelly is the right answer.

Kelly is correct when your edge estimates are themselves verified by historical performance against closing lines. If you have 500 graded bets, a verified CLV record, and a tight confidence interval on your edge size, fractional Kelly genuinely outperforms flat staking. This is rare. Most bettors who think they are in this regime are not.

If you do not have 500 graded bets and a verified CLV record, flat staking is the correct answer for you, full stop.

<div class="why-matters">
  <div class="why-matters-eyebrow">Why this matters</div>
  <div class="why-matters-text">The optimal strategy on paper is rarely the optimal strategy in practice. Flat staking is the boring answer that survives contact with the real world.</div>
</div>
