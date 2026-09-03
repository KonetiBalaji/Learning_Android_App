"""Conservative server-observed presence, not proof of attention or learning."""
from datetime import datetime

MAX_PRESENCE_GAP_SECONDS = 60


def session_seconds(db, session_id: str) -> int:
    return int(db.execute('SELECT COALESCE(SUM(seconds), 0) FROM study_time_intervals WHERE session_id = ?',
                          (session_id,)).fetchone()[0])


def record_presence(db, owner_id: str, session_id: str, observed_at: datetime) -> int:
    """Caller owns the write transaction. One owner-level cursor prevents overlap."""
    session = db.execute('SELECT * FROM mastery_sessions WHERE id = ? AND owner_id = ?',
                         (session_id, owner_id)).fetchone()
    if session is None:
        raise LookupError('Session not found')
    previous = db.execute('SELECT * FROM study_presence WHERE owner_id = ?', (owner_id,)).fetchone()
    if previous is not None:
        start = datetime.fromisoformat(previous['seen_at'])
        # Never move the watermark backward after a clock adjustment or retry.
        if observed_at <= start:
            return session_seconds(db, session_id)
        gap = (observed_at - start).total_seconds()
        end = observed_at
        if session['completed_at']:
            end = min(end, datetime.fromisoformat(session['completed_at']))
        if previous['session_id'] == session_id and gap <= MAX_PRESENCE_GAP_SECONDS and end > start:
            db.execute('INSERT INTO study_time_intervals (session_id, started_at, ended_at, seconds) VALUES (?, ?, ?, ?)',
                       (session_id, start.isoformat(), end.isoformat(), (end - start).total_seconds()))
    # A completed session cannot establish a new presence cursor or displace a
    # different ongoing session. Close its existing cursor by advancing to now.
    if not session['completed_at'] or (previous is not None and previous['session_id'] == session_id):
        db.execute('''INSERT INTO study_presence (owner_id, session_id, seen_at) VALUES (?, ?, ?)
                      ON CONFLICT(owner_id) DO UPDATE SET session_id = excluded.session_id, seen_at = excluded.seen_at''',
                   (owner_id, session_id, observed_at.isoformat()))
    return session_seconds(db, session_id)
