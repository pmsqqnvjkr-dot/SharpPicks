"""
Central SQLite path for Railway persistent volumes.
All production code (app.py, main.py, model.py, model_service.py) MUST use
get_sqlite_path() - never hardcode 'sharp_picks.db'. Railway sets
RAILWAY_VOLUME_MOUNT_PATH=/data when a volume is attached.
"""
import contextlib
import logging
import os
import sqlite3

logger = logging.getLogger(__name__)


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


# PRAGMAs run on every new connection. journal_mode=WAL is persistent
# on the database file itself so the first successful set converts
# the .db permanently; setting it on every subsequent connection is
# idempotent. synchronous and busy_timeout are per-connection and
# must be applied each time.
#
# busy_timeout=8s: short enough that a stuck lock surfaces quickly
# rather than cascading through queued cron runs. The 60s value
# tried earlier made things worse: when a write transaction stayed
# stuck (zombie connection, worker crashed mid-transaction, etc),
# every subsequent writer waited the full 60s and the closing_lines
# cron started taking 2 full minutes per run as multiple writes
# stacked up. Failing fast lets cron supervisors retry on the next
# tick instead of building a wait queue. The real fix is to find
# whoever holds locks longer than ~5s and shorten their transactions.
_CONN_PRAGMAS = (
    ('journal_mode', 'WAL'),
    ('synchronous', 'NORMAL'),
    ('busy_timeout', '8000'),  # 8s; fail fast and let supervisors retry
    ('foreign_keys', 'ON'),
)


def get_sqlite_conn(path=None, timeout=15.0):
    """Open a sqlite3 connection with WAL mode and tuned pragmas.

    All raw sqlite3 callers in the runtime should use this instead of
    sqlite3.connect() directly so journal_mode=WAL is reliably set
    before any other query runs.

    Once WAL is active on the database file, two extra files appear
    next to it on the Railway volume: sharp_picks.db-wal and
    sharp_picks.db-shm. SQLite manages them. They should not be
    deleted or excluded from the volume.

    Parameters
    ----------
    path : str, optional
        Explicit path. Defaults to get_sqlite_path(). Pass a path only
        for callers that already resolved one (e.g. admin status
        endpoints reading get_sqlite_status()['path']).
    timeout : float, default 15.0
        sqlite3.connect timeout, the window to wait for the file lock
        at connection-open time. Distinct from busy_timeout, which is
        the per-statement retry window after the connection is open.

    Returns
    -------
    sqlite3.Connection
        Caller is responsible for close().
    """
    if path is None:
        path = get_sqlite_path()
    conn = sqlite3.connect(path, timeout=timeout)
    cur = conn.cursor()
    for name, value in _CONN_PRAGMAS:
        cur.execute(f'PRAGMA {name}={value};')
    # Read back journal_mode to confirm WAL stuck. Railway volumes (ext4)
    # support WAL fine; this guards against accidentally running on a
    # filesystem that doesn't (network mounts, some shared volumes).
    actual = cur.execute('PRAGMA journal_mode;').fetchone()
    if actual and str(actual[0]).lower() != 'wal':
        logger.warning(
            'sqlite WAL pragma did not stick at %s, got journal_mode=%r. '
            'Lock contention will continue under concurrent writers.',
            path, actual[0],
        )
    cur.close()
    return conn


@contextlib.contextmanager
def sqlite_conn(path=None, timeout=15.0):
    """Context manager wrapper around get_sqlite_conn() that guarantees
    conn.close() runs even when the body raises.

    Without this, the common cron pattern -

        try:
            conn = get_sqlite_conn()
            for row in rows:
                cur.execute('UPDATE ...')   # raises OperationalError
            conn.commit()
            conn.close()
        except:
            log_error()                     # close() never reached

    leaks the connection with the implicit BEGIN's write lock held
    until Python GC eventually collects it. Subsequent cron runs and
    request handlers waiting for the write lock then time out at
    busy_timeout even though the cron looks 'finished'. This is the
    failure mode driving the cascading database-is-locked admin
    alerts after WAL + advisory lock + cron stagger were already in
    place.

    Use as:

        with sqlite_conn() as conn:
            cur = conn.cursor()
            cur.execute(...)
            conn.commit()
    """
    conn = get_sqlite_conn(path=path, timeout=timeout)
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            # Best-effort close. If the connection is already in a
            # weird state, don't propagate a secondary exception that
            # would mask the original error.
            pass


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
