"""
Central SQLite path for Railway persistent volumes.
On Railway, use RAILWAY_VOLUME_MOUNT_PATH if a volume is attached.
"""
import os


def get_sqlite_path():
    """Return path to sharp_picks.db, using persistent storage on Railway when available."""
    vol = os.environ.get('RAILWAY_VOLUME_MOUNT_PATH')
    if vol:
        return os.path.join(vol.rstrip('/'), 'sharp_picks.db')
    return os.environ.get('SQLITE_DB_PATH', 'sharp_picks.db')
