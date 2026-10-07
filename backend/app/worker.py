"""One active local worker; bounded asynchronous enrichment within each job."""
import asyncio
from contextlib import contextmanager
import fcntl
import json
import logging
from pathlib import Path
import signal

from .columns import SETTINGS
from .persistence import JobRepository, LocalArtifactStore
from .pipeline import Pipeline


class StructuredFormatter(logging.Formatter):
    def format(self, record):
        data = {"event": record.getMessage(), "level": record.levelname}
        for key in ("job_id", "stage", "source_row_number", "provider", "attempt", "latency", "error_type", "result_category"):
            if hasattr(record, key):
                data[key] = getattr(record, key)
        return json.dumps(data)


@contextmanager
def worker_lock(root):
    root.mkdir(parents=True, exist_ok=True)
    with (root / "worker.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


async def run_worker(settings=SETTINGS, stop=None, pipeline_factory=Pipeline):
    stop = stop or asyncio.Event()
    root = Path(settings.job_artifact_directory)
    repository, artifacts = JobRepository(root), LocalArtifactStore(root)
    repository.initialize()
    while not stop.is_set():
        with worker_lock(root) as acquired:
            if acquired:
                repository.recover(settings.worker_max_attempts)
                pipeline = pipeline_factory(repository, artifacts, settings)

                async def heartbeat():
                    while True:
                        repository.heartbeat()
                        await asyncio.sleep(min(settings.worker_poll_interval, settings.worker_stale_seconds / 3))

                ticker = asyncio.create_task(heartbeat())
                try:
                    while not stop.is_set():
                        repository.heartbeat()
                        job = repository.claim()
                        if job:
                            await pipeline.process(job)
                            await asyncio.sleep(0)
                        else:
                            if settings.artifact_retention_days:
                                for job_id in repository.expired_jobs(settings.artifact_retention_days):
                                    artifacts.remove(job_id)
                                    repository.delete(job_id)
                            await asyncio.sleep(settings.worker_poll_interval)
                finally:
                    ticker.cancel()
                    await asyncio.gather(ticker, return_exceptions=True)
        if not stop.is_set():
            await asyncio.sleep(settings.worker_poll_interval)


async def main():
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    logging.basicConfig(handlers=[handler], level=logging.INFO)
    stop = asyncio.Event()
    for signum in (signal.SIGTERM, signal.SIGINT):
        asyncio.get_running_loop().add_signal_handler(signum, stop.set)
    await run_worker(stop=stop)


if __name__ == "__main__":
    asyncio.run(main())
