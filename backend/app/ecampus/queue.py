"""
ecampus/queue.py

Priority queue для задач сбора данных eCampus.

Принцип работы:
  - HIGH приоритет: задачи от пользователя (открыл страницу предмета, нажал обновить)
  - LOW приоритет:  фоновый сбор всех данных

  Worker запускает не более MAX_CONCURRENT задач одновременно.
  Из них HIGH задачам отдаётся HIGH_SLOTS слотов (70%),
  LOW задачам — оставшиеся LOW_SLOTS (30%).

  Если HIGH задач нет — LOW задачи используют все слоты.

Хранение в Redis:
  ecampus:queue:high  — LPUSH/BRPOP список HIGH приоритета
  ecampus:queue:low   — LPUSH/BRPOP список LOW приоритета
  ecampus:running     — SET активных task_id
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from enum import IntEnum
from typing import Any, Callable, Coroutine

from loguru import logger


class Priority(IntEnum):
    HIGH = 1   # запрос пользователя
    LOW  = 2   # фоновый сбор


REDIS_KEY_HIGH    = "ecampus:queue:high"
REDIS_KEY_LOW     = "ecampus:queue:low"
REDIS_KEY_RUNNING = "ecampus:running"
REDIS_KEY_RESULT  = "ecampus:result:{task_id}"

MAX_CONCURRENT = 10   # всего одновременных задач
HIGH_SLOTS     = 7    # из них HIGH получает 7
LOW_SLOTS      = 3    # LOW получает 3


class ECampusTask:
    """Описание одной задачи сбора данных."""

    def __init__(
        self,
        task_type: str,         # "connect", "sync_course", "sync_all", "get_captcha"
        tg_id: int,
        priority: Priority,
        payload: dict,
        task_id: str | None = None,
    ):
        self.task_id   = task_id or str(uuid.uuid4())
        self.task_type = task_type
        self.tg_id     = tg_id
        self.priority  = priority
        self.payload   = payload
        self.created_at = time.time()

    def to_json(self) -> str:
        return json.dumps({
            "task_id":    self.task_id,
            "task_type":  self.task_type,
            "tg_id":      self.tg_id,
            "priority":   int(self.priority),
            "payload":    self.payload,
            "created_at": self.created_at,
        })

    @classmethod
    def from_json(cls, data: str) -> "ECampusTask":
        d = json.loads(data)
        return cls(
            task_type=d["task_type"],
            tg_id=d["tg_id"],
            priority=Priority(d["priority"]),
            payload=d["payload"],
            task_id=d["task_id"],
        )


class ECampusQueue:
    """
    Priority queue поверх Redis.
    Использует два отдельных списка для HIGH и LOW приоритетов.
    """

    def __init__(self):
        self._high_sem = asyncio.Semaphore(HIGH_SLOTS)
        self._low_sem  = asyncio.Semaphore(LOW_SLOTS)
        self._worker_task: asyncio.Task | None = None
        self._running = False

    def _redis(self):
        from app.cache.redis import get_redis
        return get_redis()

    async def enqueue(self, task: ECampusTask) -> str:
        """Добавляет задачу в очередь. Возвращает task_id."""
        r = self._redis()
        key = REDIS_KEY_HIGH if task.priority == Priority.HIGH else REDIS_KEY_LOW
        await r.lpush(key, task.to_json())
        logger.debug(f"Enqueued {task.task_type} [{task.priority.name}] for tg_id={task.tg_id} task_id={task.task_id}")
        return task.task_id

    async def get_result(self, task_id: str, timeout: float = 30.0) -> dict | None:
        """
        Ждёт результата задачи из Redis.
        Используется для HIGH приоритет задач где нужен ответ.
        """
        r = self._redis()
        key = REDIS_KEY_RESULT.format(task_id=task_id)
        deadline = time.time() + timeout
        while time.time() < deadline:
            raw = await r.get(key)
            if raw:
                await r.delete(key)
                return json.loads(raw)
            await asyncio.sleep(0.3)
        return None

    async def set_result(self, task_id: str, result: dict, ttl: int = 300) -> None:
        """Сохраняет результат задачи в Redis."""
        r = self._redis()
        key = REDIS_KEY_RESULT.format(task_id=task_id)
        await r.setex(key, ttl, json.dumps(result))

    async def _pop_task(self) -> ECampusTask | None:
        """
        Выбирает следующую задачу с учётом приоритета.
        HIGH задачи всегда обрабатываются раньше LOW.
        """
        r = self._redis()

        # Сначала проверяем HIGH очередь (неблокирующий pop)
        raw = await r.rpop(REDIS_KEY_HIGH)
        if raw:
            return ECampusTask.from_json(raw)

        # Затем LOW
        raw = await r.rpop(REDIS_KEY_LOW)
        if raw:
            return ECampusTask.from_json(raw)

        return None

    async def start_worker(self, handler: Callable[[ECampusTask], Coroutine]) -> None:
        """Запускает воркер который обрабатывает задачи из очереди."""
        self._running = True
        logger.info("ECampus queue worker started")

        async def run_task(task: ECampusTask):
            sem = self._high_sem if task.priority == Priority.HIGH else self._low_sem
            async with sem:
                try:
                    result = await handler(task)
                    if task.priority == Priority.HIGH:
                        await self.set_result(task.task_id, {"ok": True, "data": result})
                except Exception as e:
                    logger.error(f"Task {task.task_id} failed: {e}")
                    if task.priority == Priority.HIGH:
                        await self.set_result(task.task_id, {"ok": False, "error": str(e)})

        while self._running:
            task = await self._pop_task()
            if task:
                asyncio.create_task(run_task(task))
            else:
                await asyncio.sleep(0.5)  # ждём новых задач

    def stop_worker(self):
        self._running = False


# Глобальный экземпляр очереди
_queue: ECampusQueue | None = None


def get_queue() -> ECampusQueue:
    global _queue
    if _queue is None:
        _queue = ECampusQueue()
    return _queue
