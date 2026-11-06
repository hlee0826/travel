import asyncio
from vercel import workflow

wf = workflow.Workflows()


@wf.step(max_retries=3)
async def stage(job_id: str, attempt_id: str, name: str) -> str:
    # Workflow replay forbids the random and I/O imports used by the pipeline.
    from hosted.pipeline import run_stage
    return await asyncio.to_thread(run_stage, job_id, attempt_id, name)


@wf.workflow
async def paint(job_id: str, attempt_id: str) -> str:
    for name in ('checking_photo', 'painting', 'checking_artwork', 'rendering'):
        result = await stage(job_id, attempt_id, name)
        while result == 'busy':
            await workflow.sleep(30)
            result = await stage(job_id, attempt_id, name)
        if result != 'continue':
            return result
    return 'ready'
