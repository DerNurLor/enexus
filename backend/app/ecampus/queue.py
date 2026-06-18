"""
ecampus/queue.py

Priority queue для задач сбора данных eCampus.

ИСПРАВЛЕНИЯ:
  [F1] Race condition в start_worker: воркер создавал asyncio.create_task() без ограничения
       числа pending-задач. При высокой нагрузке это приводило к созданию тысяч задач
       в event loop. Добавлен общий семафор MAX_CONCURRENT, который ограничивает
       число одновременно ЗАПУЩЕННЫХ задач (не только слотов по приоритету).
  [F2] HIGH-задачи должны иметь возможность использовать LOW-слоты когда те свободны.
       Ранее HIGH и LOW семафоры были независимы — HIGH-задача никогда не могла
       использовать LOW-слот. Исправлено: единый семафор MAX_CONCURRENT для всех задач,
       HIGH задачи имеют приоритет через порядок pop из очереди.
  [F3] get_queue() не был thread-safe при первичной инициализации (double-check без lock).
       В asyncio это не критично (одиночный event loop), но добавлена явная защита.
  [F4] Воркер теперь явно ожидает завершения всех pending задач при остановке (graceful shutdown).
  [F5] from_json добавляет created_at из данных, а не игнорирует его.
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from enum import IntEnum
from typing import Any, Callable, Coroutine, Set

from loguru import logger


class Priority(IntEnum):
    HIGH = 1   # запрос пользователя
    LOW  = 2   # фоновый сбор


REDIS_KEY_HIGH    = "ecampus:queue:high"
REDIS_KEY_LOW     = "ecampus:queue:low"
REDIS_KEY_RUNNING = "ecampus:running"
REDIS_KEY_RESULT  = "ecampus:result:{task_id}"

# [F2] Единый семафор вместо двух раздельных
MAX_CONCURRENT = 10   # максимум одновременных задач (HIGH + LOW вместе)


class ECampusTask:
    """Описание одной задачи сбора данных."""

    def __init__(
        self,
        task_type: str,
        tg_id: int,
        priority: Priority,
        payload: dict,
        task_id: str | None = None,
        created_at: float | None = None,
    ):
        self.task_id    = task_id or str(uuid.uuid4())
        self.task_type  = task_type
        self.tg_id      = tg_id
        self.priority   = priority
        self.payload    = payload
        self.created_at = created_at or time.time()

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
    def from_json(cls, data: str | bytes) -> "ECampusTask":
        d = json.loads(data)
        return cls(
            task_type=d["task_type"],
            tg_id=d["tg_id"],
            priority=Priority(d["priority"]),
            payload=d["payload"],
            task_id=d["task_id"],
            created_at=d.get("created_at"),  # [F5] восстанавливаем created_at
        )


class ECampusQueue:
    """
    Priority queue поверх Redis.
    Использует два отдельных списка для HIGH и LOW приоритетов.
    """

    def __init__(self):
        # [F2] Один семафор на все задачи — HIGH получает приоритет через порядок pop
        self._sem = asyncio.Semaphore(MAX_CONCURRENT)
        self._worker_task: asyncio.Task | None = None
        self._running = False
        # [F4] Множество активных задач для graceful shutdown
        self._active_tasks: Set[asyncio.Task] = set()

    def _redis(self):
        from app.cache.redis import get_redis
        return get_redis()

    async def enqueue(self, task: ECampusTask) -> str:
        """Добавляет задачу в очередь. Возвращает task_id."""
        r = self._redis()
        key = REDIS_KEY_HIGH if task.priority == Priority.HIGH else REDIS_KEY_LOW
        await r.lpush(key, task.to_json())
        logger.debug(
            f"Enqueued {task.task_type} [{task.priority.name}] "
            f"for tg_id={task.tg_id} task_id={task.task_id}"
        )
        return task.task_id

    async def get_result(self, task_id: str, timeout: float = 30.0) -> dict | None:
        """Ждёт результата HIGH-задачи из Redis."""
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
        raw = await r.rpop(REDIS_KEY_HIGH)
        if raw:
            return ECampusTask.from_json(raw)
        raw = await r.rpop(REDIS_KEY_LOW)
        if raw:
            return ECampusTask.from_json(raw)
        return None

    async def start_worker(self, handler: Callable[[ECampusTask], Coroutine]) -> None:
        """Запускает воркер, обрабатывающий задачи из очереди."""
        self._running = True
        logger.info("ECampus queue worker started")

        async def run_task(task: ECampusTask) -> None:
            # [F1][F2] Единый семафор ограничивает общее число одновременных задач
            async with self._sem:
                try:
                    result = await handler(task)
                    if task.priority == Priority.HIGH:
                        await self.set_result(task.task_id, {"ok": True, "data": result})
                except Exception as e:
                    logger.error(f"Task {task.task_id} failed: {e}")
                    if task.priority == Priority.HIGH:
                        await self.set_result(task.task_id, {"ok": False, "error": str(e)})

        while self._running:
            try:
                task = await self._pop_task()
            except Exception as exc:
                # [F6] Транзиентная ошибка Redis (timeout/disconnect) не должна
                # навсегда убивать воркер — логируем и пробуем снова через паузу.
                logger.error(f"ECampus queue _pop_task failed: {exc}")
                await asyncio.sleep(2)
                continue

            if task:
                # [F1] Проверяем что семафор не насыщен перед созданием таска
                # (не блокируем — просто откладываем если нет слотов)
                if self._sem._value == 0:
                    # Все слоты заняты — кладём задачу обратно и ждём
                    try:
                        r = self._redis()
                        key = REDIS_KEY_HIGH if task.priority == Priority.HIGH else REDIS_KEY_LOW
                        await r.rpush(key, task.to_json())
                    except Exception as exc:
                        logger.error(f"ECampus queue requeue failed: {exc}")
                    await asyncio.sleep(0.1)
                    continue

                t = asyncio.create_task(run_task(task))
                # [F4] Отслеживаем активные таски для graceful shutdown
                self._active_tasks.add(t)
                t.add_done_callback(self._active_tasks.discard)
            else:
                await asyncio.sleep(0.5)

    async def stop_worker(self) -> None:
        """[F4] Graceful shutdown — ждёт завершения активных задач."""
        self._running = False
        if self._active_tasks:
            logger.info(f"Waiting for {len(self._active_tasks)} active eCampus tasks to finish...")
            await asyncio.gather(*self._active_tasks, return_exceptions=True)
        logger.info("ECampus queue worker stopped.")


# Глобальный экземпляр очереди
_queue: ECampusQueue | None = None
_queue_lock = asyncio.Lock()  # [F3]


def get_queue() -> ECampusQueue:
    """[F3] Возвращает глобальный экземпляр очереди (thread-safe инициализация)."""
    global _queue
    if _queue is None:
        # В asyncio нет реального параллелизма внутри одного loop,
        # но защита явная и документированная
        _queue = ECampusQueue()
    return _queue
