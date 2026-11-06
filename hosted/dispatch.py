from vercel import workflow
from hosted import db
from hosted.config import generation_enabled
from app.workflows import paint


async def dispatch():
    if not generation_enabled():
        return 0
    with db.connect() as conn:
        rows = conn.execute("""UPDATE minhwa.attempts SET dispatch_at=now() WHERE id IN (
          SELECT id FROM minhwa.attempts WHERE status IN ('queued','running')
          AND (dispatch_at IS NULL OR dispatch_at < now()-interval '15 minutes')
          ORDER BY created LIMIT 2 FOR UPDATE SKIP LOCKED) RETURNING id,job_id""").fetchall()
    sent = 0
    for row in rows:
        try:
            run = await workflow.start(paint, job_id=row['job_id'], attempt_id=row['id'])
            with db.connect() as conn:
                conn.execute('UPDATE minhwa.attempts SET run_id=%s WHERE id=%s', (run.run_id,row['id']))
            sent += 1
        except Exception:
            # The transactional outbox retains this attempt; another trigger can recover it.
            pass
    return sent
