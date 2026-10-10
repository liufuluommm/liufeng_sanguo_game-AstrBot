"""轻量异步定时任务引擎。

注册周期任务；插件启动时 start()，卸载时 stop()。
任务体可以是同步或异步函数；单个任务异常只记录日志不影响其它任务。
"""

from __future__ import annotations

import asyncio
import inspect
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Dict, Optional

try:  # pragma: no cover
    from astrbot.api import logger
except Exception:  # noqa: BLE001
    import logging

    logger = logging.getLogger("liufeng_sanguo_game")

JobFunc = Callable[[], Optional[Awaitable[None]]]


@dataclass
class Job:
    name: str
    func: JobFunc
    interval: int  # 秒
    run_immediately: bool = False
    last_run: float = 0.0
    run_count: int = 0
    error_count: int = 0
    next_run: float = 0.0
    enabled: bool = True
    label: str = ""
    _task: Optional[asyncio.Task] = field(default=None, repr=False)


class Scheduler:
    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def add_job(
        self,
        name: str,
        func: JobFunc,
        interval: int,
        run_immediately: bool = False,
        label: str = "",
    ) -> None:
        self._jobs[name] = Job(
            name=name,
            func=func,
            interval=max(1, int(interval)),
            run_immediately=run_immediately,
            next_run=time.time() + (0 if run_immediately else interval),
            label=label or name,
        )
        logger.info(f"[三国] 注册定时任务: {name} 间隔 {interval}s")

    def remove_job(self, name: str) -> bool:
        job = self._jobs.pop(name, None)
        return job is not None

    def jobs(self) -> Dict[str, Job]:
        return self._jobs

    def set_interval(self, name: str, seconds: int) -> bool:
        job = self._jobs.get(name)
        if not job:
            return False
        job.interval = max(1, int(seconds))
        job.next_run = time.time() + job.interval
        return True

    def set_enabled(self, name: str, enabled: bool) -> bool:
        job = self._jobs.get(name)
        if not job:
            return False
        job.enabled = bool(enabled)
        if job.enabled:
            job.next_run = time.time() + job.interval
        return True

    def job_info(self, name: str) -> Optional[Dict[str, object]]:
        job = self._jobs.get(name)
        if not job:
            return None
        return self._info(job)

    @staticmethod
    def _info(job: "Job") -> Dict[str, object]:
        return {
            "name": job.name,
            "label": job.label or job.name,
            "interval": job.interval,
            "enabled": job.enabled,
            "last_run": job.last_run,
            "run_count": job.run_count,
            "error_count": job.error_count,
            "next_run": job.next_run,
        }

    def info(self) -> list:
        return [self._info(j) for j in self._jobs.values()]

    async def run_job(self, name: str) -> None:
        job = self._jobs.get(name)
        if not job:
            return
        try:
            result = job.func()
            if inspect.isawaitable(result):
                await result
            job.last_run = time.time()
            job.run_count += 1
            job.next_run = job.last_run + job.interval
        except Exception as exc:  # noqa: BLE001
            job.error_count += 1
            logger.warning(f"[三国] 定时任务 {name} 执行失败: {exc}")

    async def _loop(self) -> None:
        while self._running:
            now = time.time()
            for job in list(self._jobs.values()):
                if job.enabled and job.next_run <= now:
                    await self.run_job(job.name)
            await asyncio.sleep(5)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        try:
            loop = asyncio.get_event_loop()
            self._task = loop.create_task(self._loop())
            logger.info("[三国] 定时任务引擎已启动")
        except RuntimeError:
            self._running = False
            logger.warning("[三国] 无可用事件循环，定时任务未启动")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            self._task = None
