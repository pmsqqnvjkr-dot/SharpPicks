"""Snapshot, list, and restore SharpPicks model pickle files.

Model pickles live on the Railway volume mount (`RAILWAY_VOLUME_MOUNT_PATH`)
alongside the SQLite database. When unset (local dev), we fall back to the
current working directory — same convention as `model.SharpPicksModel.
_default_filepath`.

This module is the helper layer behind the `/api/admin/backup-models`,
`/api/admin/list-model-backups`, and `/api/admin/restore-model` endpoints,
which gate the Phase 5 retrain cutover so we can roll back if calibration
regresses on out-of-sample data.

Backups are stored under a `_backups/` subdirectory of the volume root with
filenames of the form `<original>.<UTC-timestamp>.bak`, e.g.
`sharp_picks_mlb_model.pkl.2026-04-29T17-30-00.bak`. The timestamp suffix is
the discriminator we sort and reference by.

The functions in this module only read or copy the pickle files — they never
mutate or load them, so they cannot affect running predictions.
"""

import hashlib
import logging
import os
import shutil
from datetime import datetime

logger = logging.getLogger(__name__)

MODEL_FILENAMES = {
    'nba': 'sharp_picks_model.pkl',
    'mlb': 'sharp_picks_mlb_model.pkl',
    'wnba': 'sharp_picks_wnba_model.pkl',
}


def _model_volume_path():
    """Resolve the model storage directory (Railway volume or local fallback)."""
    return os.environ.get('RAILWAY_VOLUME_MOUNT_PATH', '.').rstrip('/')


def _backup_dir():
    d = os.path.join(_model_volume_path(), '_backups')
    os.makedirs(d, exist_ok=True)
    return d


def _sha256_of_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def backup_model(sport: str) -> dict:
    """Snapshot the current pickle for a sport. Returns metadata.

    If the source pickle is missing (e.g., model never trained for that
    sport on this environment), returns status='no_source' rather than
    raising — keeps the bulk-backup endpoint best-effort across sports.
    """
    fname = MODEL_FILENAMES.get(sport)
    if not fname:
        raise ValueError(f"Unknown sport: {sport}")
    src = os.path.join(_model_volume_path(), fname)
    if not os.path.exists(src):
        return {'sport': sport, 'status': 'no_source', 'src': src}
    ts = datetime.utcnow().strftime('%Y-%m-%dT%H-%M-%S')
    dst_name = f"{fname}.{ts}.bak"
    dst = os.path.join(_backup_dir(), dst_name)
    shutil.copy2(src, dst)
    size = os.path.getsize(dst)
    sha = _sha256_of_file(dst)
    logger.info(
        "model_backup: sport=%s src=%s dst=%s size=%d sha256=%s",
        sport, src, dst, size, sha,
    )
    return {
        'sport': sport,
        'status': 'ok',
        'src': src,
        'dst': dst,
        'backup_filename': dst_name,
        'size_bytes': size,
        'sha256': sha,
        'timestamp': ts + 'Z',
    }


def list_backups(sport: str = None) -> list:
    """List existing backups, optionally filtered by sport.

    Returned items are sorted newest-first by mtime.
    """
    d = _backup_dir()
    if not os.path.isdir(d):
        return []
    prefix = MODEL_FILENAMES.get(sport, '') if sport else ''
    if sport and not prefix:
        raise ValueError(f"Unknown sport: {sport}")
    items = []
    for name in os.listdir(d):
        if not name.endswith('.bak'):
            continue
        if prefix and not name.startswith(prefix):
            continue
        path = os.path.join(d, name)
        try:
            items.append({
                'filename': name,
                'size_bytes': os.path.getsize(path),
                'mtime': datetime.utcfromtimestamp(os.path.getmtime(path)).isoformat() + 'Z',
            })
        except OSError as e:
            logger.warning("list_backups: skipped %s: %s", name, e)
    items.sort(key=lambda x: x['mtime'], reverse=True)
    return items


def restore_model(sport: str, backup_filename: str) -> dict:
    """Restore a backup over the current pickle.

    Pre-creates a 'pre-restore' backup of whatever is currently on disk
    so the restore is itself reversible. Validates that the backup
    filename actually belongs to the requested sport (prevents e.g.
    restoring an MLB pickle as the NBA pickle by mistake).
    """
    fname = MODEL_FILENAMES.get(sport)
    if not fname:
        raise ValueError(f"Unknown sport: {sport}")
    if os.path.basename(backup_filename) != backup_filename:
        raise ValueError(f"backup_filename must be a bare filename, not a path: {backup_filename}")
    if not backup_filename.startswith(fname + '.') or not backup_filename.endswith('.bak'):
        raise ValueError(f"Backup filename {backup_filename} does not match sport {sport}")
    src = os.path.join(_backup_dir(), backup_filename)
    if not os.path.exists(src):
        raise FileNotFoundError(f"Backup not found: {src}")
    dst = os.path.join(_model_volume_path(), fname)

    pre_restore = backup_model(sport)

    shutil.copy2(src, dst)
    logger.warning(
        "model_restore: sport=%s restored_from=%s pre_restore=%s",
        sport, backup_filename, pre_restore.get('backup_filename'),
    )
    return {
        'sport': sport,
        'status': 'ok',
        'restored_from': backup_filename,
        'restored_to': dst,
        'pre_restore_backup': pre_restore.get('backup_filename'),
        'pre_restore_status': pre_restore.get('status'),
    }
