#!/usr/bin/env python3
"""
Delete the Miami pick (was published a day early).
Run: railway run python scripts/delete_miami_pick.py
Or:  DATABASE_URL=... python scripts/delete_miami_pick.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env if present
_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v

def main():
    raw = os.environ.get("SQLALCHEMY_DATABASE_URI") or os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_PRIVATE_URL") or ""
    if not raw:
        print("ERROR: No DATABASE_URL. Use railway run or set DATABASE_URL.")
        sys.exit(1)
    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://"):]

    from app import app
    from models import db, Pick, ModelRun, UserBet, TrackedBet

    with app.app_context():
        # Find Miami picks (Heat = Miami in NBA)
        miami_picks = Pick.query.filter(
            (Pick.away_team.ilike("%miami%")) | (Pick.away_team.ilike("%heat%")) |
            (Pick.home_team.ilike("%miami%")) | (Pick.home_team.ilike("%heat%"))
        ).order_by(Pick.published_at.desc()).all()

        if not miami_picks:
            print("No Miami/Heat picks found.")
            sys.exit(0)

        p = miami_picks[0]
        pick_id = p.id
        print(f"Deleting Miami pick: id={pick_id} | {p.away_team} @ {p.home_team} | game_date={p.game_date} | published={p.published_at}")

        # Clear FKs before delete
        ModelRun.query.filter_by(pick_id=pick_id).update({"pick_id": None})
        TrackedBet.query.filter_by(pick_id=pick_id).update({"pick_id": None})
        UserBet.query.filter_by(pick_id=pick_id).delete()
        db.session.delete(p)
        db.session.commit()
        print("Done. Miami pick removed.")

if __name__ == "__main__":
    main()
