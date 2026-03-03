"""
Central SQLite path for Railway persistent volumes.
All production code (app.py, main.py, model.py, model_service.py) MUST use
get_sqlite_path() — never hardcode 'sharp_picks.db'. Railway sets
RAILWAY_VOLUME_MOUNT_PATH=/data when a volume is attached.
"""
import os


def get_sqlite_path():
    """Return path to sharp_picks.db, using persistent storage on Railway when available."""
    vol = os.environ.get('RAILWAY_VOLUME_MOUNT_PATH')
    if vol:
        path = os.path.join(vol.rstrip('/'), 'sharp_picks.db')
    else:
        path = os.environ.get('SQLITE_DB_PATH', 'sharp_picks.db')
    # Ensure parent directory exists when using volume (e.g. /data)
    parent = os.path.dirname(path)
    if parent and parent != '.' and not os.path.exists(parent):
        try:
            os.makedirs(parent, exist_ok=True)
        except OSError:
            pass  # May fail if volume not writable; SQLite will fail on connect
    return path


def get_sqlite_status():
    """Return status dict for health checks and debugging."""
    vol = os.environ.get('RAILWAY_VOLUME_MOUNT_PATH')
    path = get_sqlite_path()
    exists = os.path.isfile(path)
    parent = os.path.dirname(path)
    parent_exists = os.path.isdir(parent)
    writable = os.access(parent if parent else '.', os.W_OK)
    return {
        'path': path,
        'volume_mount': vol or None,
        'file_exists': exists,
        'parent_exists': parent_exists,
        'writable': writable,
        'persistent': bool(vol),
    }
