"""Single source of truth for sport tags used in user-facing notifications.

Push titles, email subjects, and email pills should all route through
``sport_label`` so naming stays consistent across channels (NBA, MLB, WNBA).
"""

SPORT_LABELS = {
    "nba": "NBA",
    "mlb": "MLB",
    "wnba": "WNBA",
}


def sport_label(sport):
    """Return the canonical short label for a sport key (e.g. 'nba' -> 'NBA').

    Returns an empty string for falsy input. Falls back to ``sport.upper()``
    for unknown keys so a misspelling never silently strips the tag.
    """
    if not sport:
        return ""
    return SPORT_LABELS.get(sport.lower(), sport.upper())
