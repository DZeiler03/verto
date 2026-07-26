"""Multi-file forge queue for Verto / Morphix jobs."""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from morphix.base import ConversionError, ConversionResult
from morphix.engine import MorphixEngine

logger = logging.getLogger("verto.core.queue")


class JobStatus(str, Enum):
    QUEUED = "queued"
    FORGING = "forging"
    DONE = "done"  # forged in staging, ready to download
    ERROR = "error"
    CANCELLED = "cancelled"
    DOWNLOADED = "downloaded"


@dataclass
class ConversionJob:
    id: str
    source: Path
    target_format: str
    output_path: Path  # staging path while forging; may stay staged after done
    status: JobStatus = JobStatus.QUEUED
    result: ConversionResult | None = None
    error_message: str = ""
    options: dict[str, Any] = field(default_factory=dict)
    downloaded_path: Path | None = None
    downloaded_paths: list[Path] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        return self.source.name

    @property
    def is_ready_to_download(self) -> bool:
        return self.status == JobStatus.DONE and self.result is not None

    @property
    def is_downloaded(self) -> bool:
        return self.status == JobStatus.DOWNLOADED

    @property
    def staged_paths(self) -> list[Path]:
        if not self.result:
            return []
        return self.result.all_outputs


ProgressCallback = Callable[[ConversionJob], None]


class ConversionQueue:
    """Sequential forge queue that runs Morphix conversions one at a time."""

    def __init__(self, engine: MorphixEngine | None = None) -> None:
        self.engine = engine or MorphixEngine()
        self._jobs: list[ConversionJob] = []
        self._lock = threading.Lock()
        self._worker: threading.Thread | None = None
        self._stop = threading.Event()
        self._cancel_remaining = threading.Event()
        self._on_progress: ProgressCallback | None = None

    def set_progress_callback(self, cb: ProgressCallback | None) -> None:
        self._on_progress = cb

    @property
    def jobs(self) -> list[ConversionJob]:
        with self._lock:
            return list(self._jobs)

    def get_job(self, job_id: str) -> ConversionJob | None:
        with self._lock:
            for job in self._jobs:
                if job.id == job_id:
                    return job
        return None

    def add(
        self,
        source: Path | str,
        target_format: str,
        output_path: Path | str,
        options: dict[str, Any] | None = None,
    ) -> ConversionJob:
        job = ConversionJob(
            id=uuid.uuid4().hex[:12],
            source=Path(source),
            target_format=target_format,
            output_path=Path(output_path),
            options=options or {},
        )
        with self._lock:
            self._jobs.append(job)
        self._emit(job)
        return job

    def clear(self) -> None:
        with self._lock:
            self._jobs.clear()

    def clear_finished(self) -> None:
        with self._lock:
            self._jobs = [
                j
                for j in self._jobs
                if j.status in {JobStatus.QUEUED, JobStatus.FORGING}
            ]

    def ready_to_download(self) -> list[ConversionJob]:
        return [j for j in self.jobs if j.is_ready_to_download]

    def mark_downloaded(
        self,
        job_id: str,
        primary: Path,
        extras: list[Path] | None = None,
    ) -> ConversionJob | None:
        with self._lock:
            for job in self._jobs:
                if job.id == job_id:
                    job.status = JobStatus.DOWNLOADED
                    job.downloaded_path = primary
                    job.downloaded_paths = [primary, *(extras or [])]
                    self._emit(job)
                    return job
        return None

    def start(self) -> None:
        """Start background worker if not already running."""
        if self._worker and self._worker.is_alive():
            return
        self._stop.clear()
        self._cancel_remaining.clear()
        self._worker = threading.Thread(target=self._run, name="morphix-queue", daemon=True)
        self._worker.start()

    def stop(self) -> None:
        """Request stop after current job; cancel remaining queued jobs."""
        self._cancel_remaining.set()
        self._stop.set()

    def cancel_pending(self) -> int:
        """Mark all still-queued jobs as cancelled. Returns count cancelled."""
        self._cancel_remaining.set()
        cancelled = 0
        with self._lock:
            for job in self._jobs:
                if job.status == JobStatus.QUEUED:
                    job.status = JobStatus.CANCELLED
                    job.error_message = "Cancelled"
                    cancelled += 1
                    self._emit(job)
        return cancelled

    def process_all_sync(self) -> list[ConversionJob]:
        """Process all queued jobs on the current thread (useful for tests)."""
        self._cancel_remaining.clear()
        while True:
            if self._cancel_remaining.is_set():
                self.cancel_pending()
                break
            job = self._next_queued()
            if job is None:
                break
            self._execute(job)
        return self.jobs

    def _run(self) -> None:
        while not self._stop.is_set():
            if self._cancel_remaining.is_set():
                self.cancel_pending()
                break
            job = self._next_queued()
            if job is None:
                break
            self._execute(job)

    def _next_queued(self) -> ConversionJob | None:
        with self._lock:
            for job in self._jobs:
                if job.status == JobStatus.QUEUED:
                    job.status = JobStatus.FORGING
                    return job
        return None

    def _execute(self, job: ConversionJob) -> None:
        self._emit(job)
        try:
            result = self.engine.convert(
                job.source,
                job.target_format,
                job.output_path,
                job.options,
            )
            job.result = result
            job.status = JobStatus.DONE
            job.output_path = result.output_path
        except ConversionError as exc:
            job.status = JobStatus.ERROR
            job.error_message = exc.user_message
            logger.warning("Job %s failed: %s", job.id, exc)
        except Exception as exc:  # noqa: BLE001
            job.status = JobStatus.ERROR
            job.error_message = f"Unexpected error: {exc}"
            logger.exception("Job %s crashed", job.id)
        self._emit(job)

    def _emit(self, job: ConversionJob) -> None:
        if self._on_progress:
            try:
                self._on_progress(job)
            except Exception:  # noqa: BLE001
                logger.exception("Progress callback failed")
