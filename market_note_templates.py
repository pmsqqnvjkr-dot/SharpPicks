"""
Dynamic content template system for Market Notes.

Detects the day's "story" from market data and selects varied title/body/wim
templates to avoid repetitive journal entries.
"""

import random
from difflib import SequenceMatcher


TEMPLATES = {
    "SILENT_SLATE": {
        "titles": [
            "Model passes on full slate - nothing clears the filter.",
            "Zero signals tonight. The model has nothing to say.",
            "A quiet board. {games_analyzed} games analyzed, none worth a pick.",
        ],
        "bodies": [
            "{games_analyzed} games scanned, {edges_detected} edges detected, zero cleared the discipline threshold. The market is priced efficiently tonight.",
            "Every game analyzed. No edge worth acting on. The filter exists for nights like this.",
        ],
        "why_it_matters": [
            "Sitting out is a position. The model doesn't force action when the math isn't there.",
            "Discipline means passing more often than picking. Tonight proves the filter works.",
        ],
    },
    "HIGH_DENSITY": {
        "titles": [
            "The board is loaded - {signals_generated} signals from {edges_detected} edges.",
            "Signal density at {signal_density:.0f}%. The market is mispricing tonight.",
            "Rare density: more than half the edges cleared the filter.",
        ],
        "bodies": [
            "{signals_generated} of {edges_detected} edges passed discipline. Signal density at {signal_density:.0f}% - well above the typical 25-35% range. The market is offering unusual breadth tonight.",
            "High conviction night. {signals_generated} signals generated across {games_analyzed} games. When density spikes like this, the market is collectively mispricing the slate.",
        ],
        "why_it_matters": [
            "High density nights are rare. When the model finds this much opportunity, it usually means the market hasn't adjusted to something yet.",
            "Breadth matters as much as depth. One big edge is noise - multiple edges across the slate is a market signal.",
        ],
    },
    "LONE_WOLF": {
        "titles": [
            "One game stands out - {top_edge_team} showing {top_edge_pct:.0f}% edge.",
            "The entire slate narrows to one pick: {top_edge_team}.",
            "Single conviction: {top_edge_team} at +{top_edge_pct:.0f}% while the rest stays flat.",
        ],
        "bodies": [
            "{games_analyzed} games analyzed, one signal generated. {top_edge_team} is the outlier at +{top_edge_pct:.1f}% adjusted edge. Everything else fell below threshold.",
            "When the model isolates a single game from a full slate, it usually means one matchup is genuinely mispriced while the rest of the market is tight.",
        ],
        "why_it_matters": [
            "The model's best nights aren't the busiest ones. Concentrated conviction often outperforms scattered action.",
            "One strong signal from a crowded slate is more telling than five weak ones.",
        ],
    },
    "DOG_SWEEP": {
        "titles": [
            "Underdogs across the board - {underdog_edges} edges, zero on chalk.",
            "The market is overpricing every favorite tonight.",
            "Full underdog sweep: {underdog_edges} edges, all on dogs.",
        ],
        "bodies": [
            "{underdog_edges} edges detected, every one on an underdog. The market is systematically overvaluing favorites tonight. {signals_generated} cleared the filter.",
            "Zero favorite edges. {underdog_edges} underdog edges. The spread market is running wide and the model sees value on the other side of every line.",
        ],
        "why_it_matters": [
            "When underdogs sweep the edge board, it usually means public money is inflating chalk. That's where the model finds room.",
            "A full underdog sweep is uncommon. The market tends to overprice favorites when public sentiment runs hot.",
        ],
    },
    "CHALK_SWEEP": {
        "titles": [
            "Favorites showing edge tonight - {favorite_edges} signals, all on chalk.",
            "Rare chalk sweep: the model likes the favorites.",
            "Underdogs quiet tonight - all {favorite_edges} edges favor the chalk.",
        ],
        "bodies": [
            "Every edge tonight sits with a favorite. {favorite_edges} edges detected, {signals_generated} cleared the filter. The market may be underpricing the top side.",
            "The model doesn't have a structural bias for dogs or chalk - it follows the math. Tonight the math says favorites are undervalued.",
        ],
        "why_it_matters": [
            "Chalk sweeps are less common than dog sweeps. When the model agrees with the market direction but not the magnitude, favorites become the value play.",
            "Public money usually inflates favorites. When the model still finds edge on chalk despite that, the mispricing is worth noting.",
        ],
    },
    "DOG_LEAN": {
        "titles": [
            "Underdogs showing unusual value - {underdog_edges} of {edges_detected} edges on dogs.",
            "Dogs leading the edge board: {underdog_edges} underdog vs {favorite_edges} favorite.",
            "Value sitting with the underdogs tonight - {signals_generated} signals, mostly dogs.",
        ],
        "bodies": [
            "{edges_detected} edges detected with a clear lean: {underdog_edges} on underdogs, {favorite_edges} on favorites. {signals_generated} passed the discipline filter at {signal_density:.0f}% density.",
            "The underdog side is where the model is finding room. {underdog_edges} edges on dogs against {favorite_edges} on favorites, with {signals_generated} clearing the threshold.",
        ],
        "why_it_matters": [
            "When underdogs cluster with edge, the market may be overvaluing name recognition. That's where discipline finds value.",
            "An underdog lean suggests the spread market is running a point or two wide on several games. Small inefficiencies add up.",
        ],
    },
    "CHALK_LEAN": {
        "titles": [
            "Favorites dominating the edge board - {favorite_edges} of {edges_detected} on chalk.",
            "Market underpricing favorites tonight. {favorite_edges} edges on the top side.",
            "Chalk finding value: {signals_generated} signals lean toward favorites.",
        ],
        "bodies": [
            "{favorite_edges} favorite edges vs {underdog_edges} underdog. The model sees the favorites as underpriced relative to their lines. {signals_generated} passed the filter.",
            "Unusual night - the model is siding with the chalk. {favorite_edges} edges on favorites, {signals_generated} clearing discipline.",
        ],
        "why_it_matters": [
            "When the model backs favorites, it means the lines haven't caught up to the matchup reality. The public already bet these teams up - and the model still sees room.",
            "Favorite value is counterintuitive. The market moves chalk prices higher with public money, but sometimes not far enough.",
        ],
    },
    "STREAK": {
        "titles": [
            "Day {consecutive_same_bias} of the {bias_direction} lean. Pattern holding.",
            "{bias_direction} value streak: {consecutive_same_bias} straight days.",
            "The {bias_direction} lean continues - market still hasn't adjusted.",
        ],
        "bodies": [
            "{consecutive_same_bias} consecutive days with the model leaning {bias_direction}. Today: {underdog_edges} dog edges, {favorite_edges} favorite edges, {signals_generated} signals. The market hasn't corrected the structural lean yet.",
            "Streaks like this happen when the market has a persistent blind spot. Day {consecutive_same_bias} of {bias_direction} value - {signals_generated} signals today.",
        ],
        "why_it_matters": [
            "Multi-day streaks mean the market is slow to correct. Each day the lean persists is another data point that the inefficiency is real.",
            "When the same pattern repeats for {consecutive_same_bias} days, it's not noise. The market is structurally mispricing one side.",
        ],
    },
    "WIDE_SPREADS": {
        "titles": [
            "Big spreads, big edges - value hiding in the blowout lines.",
            "The market is struggling with lopsided matchups tonight.",
            "Double-digit spreads showing the most opportunity.",
        ],
        "bodies": [
            "Tonight's edges cluster in high-spread games (avg spread {spread_mag_avg:.1f}). The market tends to misprice blowout lines because the public ignores them. The model doesn't.",
            "Value in the margins: {signals_generated} signals from games averaging {spread_mag_avg:.1f}-point spreads. Big lines create big inefficiencies.",
        ],
        "why_it_matters": [
            "Blowout lines are the least efficient part of the spread market. Lower betting volume means less price discovery - and more room for the model.",
            "Casual bettors skip lopsided games. That's exactly where systematic models find their biggest edges.",
        ],
    },
    "BALANCED": {
        "titles": [
            "Even split tonight - edges on both sides of the board.",
            "No directional lean: {favorite_edges} chalk, {underdog_edges} dogs.",
            "Balanced board with {signals_generated} signals and no clear bias.",
        ],
        "bodies": [
            "The model sees value on both sides: {favorite_edges} favorite edges, {underdog_edges} underdog edges. {signals_generated} cleared the filter. No structural lean - each game is its own story tonight.",
            "Balanced nights suggest the market is mispricing individual matchups rather than systematically leaning one way. {signals_generated} signals across {games_analyzed} games.",
        ],
        "why_it_matters": [
            "A balanced edge board means the market isn't making a directional mistake - it's making matchup-specific ones. That's harder to exploit but the model is built for it.",
            "No lean means the model is finding idiosyncratic value, not a market-wide pattern. These signals tend to be more durable.",
        ],
    },
    "STANDARD": {
        "titles": [
            "{signals_generated} signals from tonight's {games_analyzed}-game slate.",
            "Model finds {signals_generated} opportunities across {edges_detected} edges.",
            "Edge scan complete: {signals_generated} picks clear the filter.",
        ],
        "bodies": [
            "{games_analyzed} games analyzed, {edges_detected} edges detected, {signals_generated} cleared discipline at {signal_density:.0f}% density. {underdog_edges} underdog edges, {favorite_edges} favorite edges.",
            "Tonight's scan: {edges_detected} edges, {signals_generated} signals. Top edge at +{top_edge_pct:.1f}% on {top_edge_team}. The filter is working as designed.",
        ],
        "why_it_matters": [
            "Every night is a data point. The model doesn't chase narratives - it follows the numbers.",
            "Consistency matters more than any single night. The process is the edge.",
        ],
    },
}


def detect_story(data):
    """Classify today's data profile into a story type. First match wins."""
    d = data

    if d["signals_generated"] == 0:
        return "SILENT_SLATE"

    if d["signal_density"] >= 50:
        return "HIGH_DENSITY"

    if d["signals_generated"] == 1 and d["top_edge_pct"] >= 7:
        return "LONE_WOLF"

    if d["favorite_edges"] == 0 and d["underdog_edges"] >= 3:
        return "DOG_SWEEP"
    if d["underdog_edges"] == 0 and d["favorite_edges"] >= 3:
        return "CHALK_SWEEP"

    if d["underdog_edges"] >= d["favorite_edges"] * 2 and d["favorite_edges"] > 0:
        return "DOG_LEAN"
    if d["favorite_edges"] >= d["underdog_edges"] * 2 and d["underdog_edges"] > 0:
        return "CHALK_LEAN"

    if d["consecutive_same_bias"] >= 3:
        return "STREAK"

    if d["spread_mag_avg"] >= 10:
        return "WIDE_SPREADS"

    if abs(d["favorite_edges"] - d["underdog_edges"]) <= 1:
        return "BALANCED"

    return "STANDARD"


def is_too_similar(new_title, prev_title, threshold=0.6):
    """Returns True if the new title is too similar to yesterday's."""
    if not prev_title:
        return False
    ratio = SequenceMatcher(None, new_title.lower(), prev_title.lower()).ratio()
    return ratio > threshold


def select_template(story_type, data):
    """Pick a title/body/wim combo, avoiding yesterday's title."""
    story = TEMPLATES.get(story_type, TEMPLATES["STANDARD"])

    for title_template in random.sample(story["titles"], len(story["titles"])):
        try:
            title = title_template.format(**data)
        except (KeyError, ValueError):
            continue
        if not is_too_similar(title, data.get("prev_note_title")):
            body = random.choice(story["bodies"])
            wim = random.choice(story["why_it_matters"])
            try:
                body = body.format(**data)
                wim = wim.format(**data)
            except (KeyError, ValueError):
                pass
            return title, body, wim, story_type

    fallback = TEMPLATES["STANDARD"]
    title_template = random.choice(fallback["titles"])
    body_template = random.choice(fallback["bodies"])
    wim_template = random.choice(fallback["why_it_matters"])
    try:
        title = title_template.format(**data)
        body = body_template.format(**data)
        wim = wim_template.format(**data)
    except (KeyError, ValueError):
        title = f"{data.get('signals_generated', 0)} signals from tonight's slate."
        body = f"{data.get('games_analyzed', 0)} games analyzed."
        wim = "The process is the edge."
    return title, body, wim, "STANDARD"


def generate_market_note(report, prev_note_title=None, consecutive_same_bias=0):
    """
    Main entry point. Takes the market report dict plus contextual data,
    returns (title, body, why_it_matters, story_type).
    """
    lean = report.get('market_lean') or {}
    fav = lean.get('favorites', 0)
    udog = lean.get('underdogs', 0)

    if udog > fav:
        bias_direction = "underdog"
    elif fav > udog:
        bias_direction = "favorite"
    else:
        bias_direction = "neutral"

    data = {
        "edges_detected": report.get('edges_detected', 0),
        "signals_generated": report.get('qualified_signals', 0),
        "signal_density": float(report.get('signal_density', 0)),
        "games_analyzed": report.get('games_analyzed', 0),
        "favorite_edges": fav,
        "underdog_edges": udog,
        "top_edge_pct": float(report.get('top_edge_pct', 0)),
        "top_edge_team": report.get('top_edge_team') or report.get('largest_edge_game') or 'N/A',
        "regime": report.get('regime', 'NORMAL'),
        "nei": report.get('market_efficiency_index', 0),
        "implication": report.get('regime_micro', ''),
        "prev_note_title": prev_note_title,
        "consecutive_same_bias": consecutive_same_bias,
        "spread_mag_avg": float(report.get('spread_mag_avg', 0)),
        "bias_direction": bias_direction,
    }

    story_type = detect_story(data)
    title, body, wim, resolved_type = select_template(story_type, data)

    if title and not title[0].isupper():
        title = title[0].upper() + title[1:]

    return title, body, wim, resolved_type
