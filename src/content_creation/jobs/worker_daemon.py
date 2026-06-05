"""Worker Daemon implementation responsible for dequeuing and executing background jobs."""

import dataclasses
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import threading
import time
from typing import Any, Dict, List, Optional
from uuid import UUID

from content_creation.jobs.lock_manager import LockManager
from content_creation.jobs.lock_models import LockStatus, LockType, ResourceLock
from content_creation.jobs.models import Job, JobResult, JobStatus, JobType
from content_creation.jobs.queue_engine import QueueEngine
from content_creation.jobs.repository import JobRepository
from content_creation.workflow.workflow_action_executor import WorkflowActionExecutor

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WorkerConfig:
    """Configuration options for a WorkerDaemon instance."""

    poll_interval_seconds: float
    heartbeat_interval_seconds: float
    zombie_timeout_seconds: float
    max_concurrent_jobs: int
    worker_id: str

    def __post_init__(self) -> None:
        """Validate worker intervals and boundaries."""
        if self.poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be positive")
        if self.heartbeat_interval_seconds <= 0:
            raise ValueError("heartbeat_interval_seconds must be positive")
        if self.zombie_timeout_seconds <= 0:
            raise ValueError("zombie_timeout_seconds must be positive")
        if self.max_concurrent_jobs < 1:
            raise ValueError("max_concurrent_jobs must be at least 1")


@dataclass(frozen=True)
class WorkerExecutionResult:
    """Outcome of a single job execution cycle."""

    success: bool
    job_id: str
    duration_seconds: float
    events_emitted: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


class HeartbeatThread(threading.Thread):
    """Auxiliary background thread executing heartbeats for active jobs."""

    def __init__(self, repo: JobRepository, job_id: UUID, interval: float, stop_event: threading.Event) -> None:
        super().__init__()
        self.repo = repo
        self.job_id = job_id
        self.interval = interval
        self.stop_event = stop_event
        self.daemon = True

    def run(self) -> None:
        """Periodically trigger the heartbeat repository API."""
        while not self.stop_event.wait(self.interval):
            try:
                self.repo.heartbeat(self.job_id)
            except Exception as e:
                logger.warning(f"Failed to update heartbeat for job {self.job_id}: {e}")


class WorkerDaemon:
    """Cooperative background worker daemon claiming and executing jobs."""

    def __init__(
        self,
        ctx: Any,
        queue_engine: QueueEngine,
        lock_manager: LockManager,
        executor: Optional[WorkflowActionExecutor] = None,
        config: Optional[WorkerConfig] = None,
    ) -> None:
        self._ctx = ctx
        self._queue = queue_engine
        self._locks = lock_manager
        self._executor = executor or WorkflowActionExecutor()
        self._config = config or WorkerConfig(
            poll_interval_seconds=2.0,
            heartbeat_interval_seconds=10.0,
            zombie_timeout_seconds=30.0,
            max_concurrent_jobs=1,
            worker_id=f"worker_{threading.get_ident()}",
        )
        self._repo = queue_engine._repo
        self._is_running = False
        self._main_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the background execution daemon thread."""
        if self._is_running:
            return
        self._is_running = True
        self._main_thread = threading.Thread(target=self.run_forever, daemon=True)
        self._main_thread.start()
        logger.info(f"WorkerDaemon {self._config.worker_id} started successfully.")

    def stop(self) -> None:
        """Gracefully stop the background polling loop."""
        self._is_running = False
        if self._main_thread:
            self._main_thread.join(timeout=5.0)
        logger.info(f"WorkerDaemon {self._config.worker_id} stopped.")

    def _acquire_locks(self, job: Job) -> Optional[List[ResourceLock]]:
        """Acquire Calendar -> Topic -> Manifest locks in hierarchical order.

        Returns list of locks if successful, or None if any lock target is busy.
        """
        acquired = []
        try:
            # 1. Calendar Lock (PLAN_WEEK, DRY_RUN)
            if job.job_type in (JobType.PLAN_WEEK.value, JobType.DRY_RUN.value) and job.target_id != "all":
                lock = self._locks.acquire_calendar_lock(job.job_id, job.target_id)
                acquired.append(lock)

            # 2. Topic Lock (GENERATE_BRIEF, CI, STORYBOARD, ASSET, or topic target)
            if (
                job.job_type in (
                    JobType.GENERATE_BRIEF.value,
                    JobType.GENERATE_CI.value,
                    JobType.GENERATE_STORYBOARD.value,
                    JobType.GENERATE_ASSET.value
                ) or job.target_type == "topic"
            ) and job.target_id != "all":
                lock = self._locks.acquire_topic_lock(job.job_id, job.target_id)
                acquired.append(lock)

            # 3. Manifest Lock (BUILD_MANIFEST)
            if (job.job_type == JobType.BUILD_MANIFEST.value or job.target_type == "manifest") and job.target_id != "all":
                lock = self._locks.acquire_manifest_lock(job.job_id, job.target_id)
                acquired.append(lock)

            return acquired

        except ValueError:
            # Target lock contention -> Release acquired locks in reverse order
            self._release_locks(acquired)
            return None

    def _release_locks(self, locks: List[ResourceLock]) -> None:
        """Release acquired locks in reverse order (Manifest -> Topic -> Calendar)."""
        for lock in reversed(locks):
            try:
                self._locks.release_lock(lock.lock_id)
            except Exception as e:
                logger.warning(f"Error releasing lock {lock.lock_id}: {e}")

    def run_once(self) -> Optional[WorkerExecutionResult]:
        """Claim, lock, execute, and persist a single background job iteration."""
        # 1. Claim next job
        job = self._queue.claim_next_job(self._config.worker_id)
        if not job:
            return None

        # Emit job_started event immediately after claiming
        try:
            from content_creation.events.bus import get_event_bus
            from content_creation.events.factory import create_job_event
            from content_creation.events.models import EventType
            bus = get_event_bus()
            evt = create_job_event(
                event_type=EventType.JOB_STARTED,
                job_id=job.job_id,
                job_type=job.job_type,
                status=JobStatus.RUNNING.value,
                operator_id=job.operator_id,
                correlation_id=job.correlation_id,
                target_type=job.target_type,
                target_id=job.target_id,
                retry_count=job.retry_count,
                max_retries=job.max_retries,
            )
            bus.publish(evt)
        except Exception:
            pass

        start_time = datetime.now(timezone.utc)
        locks = None
        stop_event = threading.Event()
        heartbeat_thread = None

        try:
            # Check cancellation status immediately after claiming
            db_job = self._repo.get_job(job.job_id)
            if not db_job or db_job.status == JobStatus.CANCELLED:
                try:
                    from content_creation.events.bus import get_event_bus
                    from content_creation.events.factory import create_job_event
                    from content_creation.events.models import EventType
                    bus = get_event_bus()
                    evt = create_job_event(
                        event_type=EventType.JOB_CANCELLED,
                        job_id=job.job_id,
                        job_type=job.job_type,
                        status=JobStatus.CANCELLED.value,
                        operator_id=job.operator_id,
                        correlation_id=job.correlation_id,
                        target_type=job.target_type,
                        target_id=job.target_id,
                        retry_count=job.retry_count,
                        max_retries=job.max_retries,
                    )
                    bus.publish(evt)
                except Exception:
                    pass
                return WorkerExecutionResult(
                    success=False,
                    job_id=str(job.job_id),
                    duration_seconds=0.0,
                    error_message="Job was cancelled before execution started.",
                )

            # 2. Lock resources
            locks = self._acquire_locks(job)
            if locks is None:
                # Lock contention: reschedule execution by resetting back to QUEUED
                # Set run_after to 5 seconds from now to prevent tight loop collisions
                from datetime import timedelta
                run_after_time = datetime.now(timezone.utc) + timedelta(seconds=5)
                self._repo.update_job(
                    dataclasses.replace(
                        job,
                        status=JobStatus.QUEUED,
                        started_at=None,
                        last_heartbeat=None,
                        run_after=run_after_time,
                    )
                )
                return WorkerExecutionResult(
                    success=False,
                    job_id=str(job.job_id),
                    duration_seconds=0.0,
                    warnings=["Lock unavailable; job returned to queue."],
                    error_message="Lock unavailable",
                )

            # 3. Spin up heartbeat thread
            heartbeat_thread = HeartbeatThread(
                self._repo,
                job.job_id,
                self._config.heartbeat_interval_seconds,
                stop_event,
            )
            heartbeat_thread.start()

            # Verify status before invoking executor
            db_job = self._repo.get_job(job.job_id)
            if not db_job or db_job.status == JobStatus.CANCELLED:
                try:
                    from content_creation.events.bus import get_event_bus
                    from content_creation.events.factory import create_job_event
                    from content_creation.events.models import EventType
                    bus = get_event_bus()
                    evt = create_job_event(
                        event_type=EventType.JOB_CANCELLED,
                        job_id=job.job_id,
                        job_type=job.job_type,
                        status=JobStatus.CANCELLED.value,
                        operator_id=job.operator_id,
                        correlation_id=job.correlation_id,
                        target_type=job.target_type,
                        target_id=job.target_id,
                        retry_count=job.retry_count,
                        max_retries=job.max_retries,
                    )
                    bus.publish(evt)
                except Exception:
                    pass
                raise ValueError("Job cancelled before service dispatch")

            # 4. Dispatch action execution to WorkflowActionExecutor
            action_id = job.payload.get("action_id", job.job_type.lower())
            executor_res = self._executor.execute(
                ctx=self._ctx,
                action_id=action_id,
                target_artifact_type=job.target_type,
                target_artifact_id=job.target_id,
                payload=job.payload,
                operator_id=job.operator_id,
            )

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            # Stop heartbeat updates immediately
            stop_event.set()
            if heartbeat_thread:
                heartbeat_thread.join(timeout=1.0)

            # Verify if job was cancelled out-of-band during execution
            db_job = self._repo.get_job(job.job_id)
            if db_job and db_job.status == JobStatus.CANCELLED:
                try:
                    from content_creation.events.bus import get_event_bus
                    from content_creation.events.factory import create_job_event
                    from content_creation.events.models import EventType
                    bus = get_event_bus()
                    evt = create_job_event(
                        event_type=EventType.JOB_CANCELLED,
                        job_id=job.job_id,
                        job_type=job.job_type,
                        status=JobStatus.CANCELLED.value,
                        operator_id=job.operator_id,
                        correlation_id=job.correlation_id,
                        target_type=job.target_type,
                        target_id=job.target_id,
                        retry_count=job.retry_count,
                        max_retries=job.max_retries,
                    )
                    bus.publish(evt)
                except Exception:
                    pass
                return WorkerExecutionResult(
                    success=False,
                    job_id=str(job.job_id),
                    duration_seconds=duration,
                    error_message="Job was cancelled during execution.",
                )

            # 5. Handle executor results and status updates
            if executor_res.success:
                job_res = JobResult(
                    duration_seconds=duration,
                    warnings=executor_res.warnings,
                    emitted_events=executor_res.emitted_events,
                    generated_files=executor_res.affected_artifacts,
                    metadata={"execution_status": executor_res.execution_status.value},
                )
                self._repo.complete_job(job.job_id, job_res)
                try:
                    from content_creation.events.bus import get_event_bus
                    from content_creation.events.factory import create_job_event
                    from content_creation.events.models import EventType
                    bus = get_event_bus()
                    evt = create_job_event(
                        event_type=EventType.JOB_COMPLETED,
                        job_id=job.job_id,
                        job_type=job.job_type,
                        status=JobStatus.COMPLETED.value,
                        operator_id=job.operator_id,
                        correlation_id=job.correlation_id,
                        target_type=job.target_type,
                        target_id=job.target_id,
                        retry_count=job.retry_count,
                        max_retries=job.max_retries,
                        extra_payload={
                            "duration_seconds": duration,
                            "warnings": executor_res.warnings,
                            "emitted_events": executor_res.emitted_events,
                        }
                    )
                    bus.publish(evt)
                except Exception:
                    pass
                return WorkerExecutionResult(
                    success=True,
                    job_id=str(job.job_id),
                    duration_seconds=duration,
                    events_emitted=executor_res.emitted_events,
                    warnings=executor_res.warnings,
                )
            else:
                error_msg = "; ".join(executor_res.blocking_reasons) or "Execution failed"
                self._queue.schedule_retry(job.job_id, error_msg)
                return WorkerExecutionResult(
                    success=False,
                    job_id=str(job.job_id),
                    duration_seconds=duration,
                    error_message=error_msg,
                )

        except Exception as e:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            stop_event.set()
            if heartbeat_thread:
                try:
                    heartbeat_thread.join(timeout=1.0)
                except Exception:
                    pass

            db_job = self._repo.get_job(job.job_id)
            if db_job and db_job.status == JobStatus.CANCELLED:
                return WorkerExecutionResult(
                    success=False,
                    job_id=str(job.job_id),
                    duration_seconds=duration,
                    error_message="Job was cancelled.",
                )

            error_msg = str(e)
            try:
                self._queue.schedule_retry(job.job_id, error_msg)
            except Exception:
                pass
            return WorkerExecutionResult(
                success=False,
                job_id=str(job.job_id),
                duration_seconds=duration,
                error_message=error_msg,
            )

        finally:
            # 6. Release target locks
            if locks:
                self._release_locks(locks)

    def run_forever(self) -> None:
        """Poll the queue indefinitely in a sleep-retry loop."""
        while self._is_running:
            try:
                res = self.run_once()
                if not res:
                    # Queue is empty, sleep for configured poll interval
                    time.sleep(self._config.poll_interval_seconds)
            except Exception as e:
                logger.error(f"Error in worker polling loop: {e}")
                time.sleep(self._config.poll_interval_seconds)
