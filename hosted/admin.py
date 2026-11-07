"""Operator-only CLI. Uses server credentials, never a browser session."""
import argparse
import json
import os
from pathlib import Path
from hosted import storage
from hosted import db
from hosted.pipeline import render_files


def decide(job_id, decision, note):
    if len(note.strip()) < 12:
        raise ValueError('Record the checks made and the reason for this decision.')
    with db.connect() as conn:
        doc = db.job(conn, job_id, lock=True)['document']
        attempt = doc.get('attempt_id')
        if decision == 'reconcile':
            if doc['status'] != 'uncertain':
                raise ValueError('Only an uncertain attempt can be reconciled.')
            running = conn.execute("SELECT 1 FROM minhwa.steps WHERE attempt_id=%s AND status='running' AND started>now()-interval '15 minutes'", (attempt,)).fetchone()
            if running:
                raise ValueError('Wait for the in-flight request to end before reconciling.')
            conn.execute("UPDATE minhwa.steps SET status='uncertain' WHERE attempt_id=%s AND status='running'",(attempt,))
            doc.update(status='failed', error='The interrupted attempt was checked. You may try again.')
        else:
            if doc['status'] != 'awaiting_review':
                raise ValueError('Only a flagged painting can be reviewed.')
            if decision == 'approve':
                candidate = render_files(doc, attempt)
                doc['candidates'].append(candidate)
                doc.update(status='ready', error=None, completed_batches=doc['completed_batches']+1)
            else:
                doc.update(status='rejected', error='The painting did not pass the studio review. You may try again.')
        conn.execute('UPDATE minhwa.attempts SET status=%s,reconciliation=%s WHERE id=%s', (doc['status'],note,attempt))
        db.save_job(conn, doc)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['list','inspect','approve','reject','reconcile'])
    parser.add_argument('--job')
    parser.add_argument('--note', default='')
    parser.add_argument('--directory', type=Path)
    args=parser.parse_args()
    if args.action=='list':
        with db.connect() as conn:
            rows=conn.execute("SELECT id,document->>'status' AS status FROM minhwa.jobs WHERE document->>'status' IN ('uncertain','awaiting_review')").fetchall()
        print(json.dumps(rows))
    elif args.action=='inspect':
        if not args.directory:
            parser.error('Provide a new private --directory for review files.')
        args.directory.mkdir(mode=0o700,parents=True,exist_ok=False)
        with db.connect() as conn:
            doc=db.job(conn,args.job)['document']
            reviews=conn.execute('SELECT name,result FROM minhwa.steps WHERE attempt_id=%s',(doc['attempt_id'],)).fetchall()
        for filename,key in [('source.png',args.job+'/source.png'),('painting.png',f'{args.job}/{doc["attempt_id"]}/artwork.png')]:
            output=args.directory/filename
            output.write_bytes(storage.read('art',key));output.chmod(0o600)
        output=args.directory/'review.json';output.write_text(json.dumps(reviews,indent=2));output.chmod(0o600)
        print('Private review files saved in the selected directory.')
    else:
        decide(args.job,args.action,args.note)
        print('Studio decision saved.')

if __name__=='__main__':
    main()
