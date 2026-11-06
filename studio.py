"""Codex handoff: list pending work, attach built-in image tool outputs, or mark failure."""
import argparse
import json
from pathlib import Path
from server import DATA, job_path, read_json, save_json, complete_artwork, review_candidate, reconcile_attempt, LOCK
from generation import estimated_cost


def complete(job_id, images):
    return complete_artwork(job_id, [Path(path).read_bytes() for path in images])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('pending')
    commands.add_parser('metrics', help='Report completed calls, estimated credit use, and review outcomes without photo data.')
    review = commands.add_parser('review', help='Record a studio review of a flagged painting.')
    review.add_argument('job_id')
    review.add_argument('candidate_id')
    review.add_argument('--decision', choices=('approve', 'reject'), required=True)
    review.add_argument('--note', required=True)
    review.add_argument('--override', action='store_true', help='Explicitly override an automated concern after inspecting all images.')
    review.add_argument('--reviewer', choices=('operator', 'codex-qa'), default='operator')
    reconcile = commands.add_parser('reconcile', help='Unlock an uncertain attempt after checking provider usage.')
    reconcile.add_argument('job_id')
    reconcile.add_argument('--note', required=True)
    done = commands.add_parser('complete')
    done.add_argument('job_id')
    done.add_argument('images', nargs='+')
    failed = commands.add_parser('fail')
    failed.add_argument('job_id')
    failed.add_argument('reason')
    args = parser.parse_args()
    if args.command == 'metrics':
        rows = []
        with LOCK:
            for file in (DATA / 'jobs').glob('*/job.json'):
                job = read_json(file)
                for attempt in job.get('attempts', []):
                    calls = attempt.get('calls', {})
                    costs = [estimated_cost(c.get('model'), c.get('usage')) for c in calls.values()]
                    rows.append({'job_id': job['id'], 'attempt_id': attempt['id'], 'style': job['style'],
                        'status': attempt['status'], 'reserved_cents': attempt['reserved_cents'],
                        'known_cost_estimate_usd': round(sum(c for c in costs if c is not None), 6),
                        'calls_without_cost': sum(c is None for c in costs),
                        'seconds': round(max((c.get('finished', c['started']) for c in calls.values()), default=attempt['created']) - attempt['created'], 1)})
        print(json.dumps(rows, indent=2))
    elif args.command == 'pending':
        with LOCK:
            pending = [j for p in (DATA / 'jobs').glob('*/job.json') if (j := read_json(p))['status'] in ('awaiting_artwork', 'awaiting_review', 'uncertain')]
        for job in pending:
            print(f"{job['id']} | {job['status']} | {job['style']} | {job_path(job['id'])}")
            for candidate in job['candidates']:
                if candidate.get('review_status') == 'pending':
                    print(candidate['id'], candidate.get('quality_report'))
        if not pending:
            print('No pending portraits.')
    elif args.command == 'review':
        job = review_candidate(args.job_id, args.candidate_id, args.decision == 'approve', args.note, args.override, args.reviewer)
        print('Review saved:', job['status'])
    elif args.command == 'reconcile':
        job = reconcile_attempt(args.job_id, args.note)
        print('Reconciliation saved:', job['status'])
    elif args.command == 'complete':
        job = complete(args.job_id, args.images)
        print(f"Attached {len(args.images)} artwork(s) to {job['id']}. Refresh the studio or wait for its next update.")
    elif args.command == 'fail':
        with LOCK:
            folder = job_path(args.job_id)
            job = read_json(folder / 'job.json')
            if job['status'] != 'awaiting_artwork':
                raise ValueError('Only a pending manual job can be marked failed.')
            job['status'], job['error'] = 'failed', args.reason[:200]
            save_json(folder / 'job.json', job)
        print('Marked failed. Retry allowance has not been consumed.')

if __name__ == '__main__':
    main()
