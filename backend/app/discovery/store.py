"""发现层快照存储 + 加速计算 —— 发现系统的"记忆"。

为什么需要它: 搜索是无状态的 (每次重新查); 发现必须有记忆。
"加速"= 今天的信号 vs 上次的信号。没有昨天的快照, 就只能看"最大",
而"最大"= 已出圈 = 看到就迟了。存快照、比 delta, 才能抓住"从低基数在长"。

用独立 discovery.db (stdlib sqlite3), 与 dossier.db 解耦, 让发现层自包含。

两张表:
- snapshot: 每次运行 (run) 对每条 item 的一行记录 (signal/engagement 随时间变化)
- item_seen: 每条 item 的首见信息 (first_seen_at), 用于判定"全新苗头"
"""
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app import config
from app.discovery.sources import DiscoveryItem


def _hours_between(start_iso: str, end_iso: str) -> Optional[float]:
    """两个 ISO 时间戳之间的小时差 (end - start)。

    无法解析时返回 None —— 调用方据此降级到 is_new 判定 (测试里用非 ISO
    run_id 如 'day1' 时即走此降级路径, 不影响逻辑)。
    """
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    try:
        start = datetime.strptime(start_iso, fmt)
        end = datetime.strptime(end_iso, fmt)
    except (ValueError, TypeError):
        return None
    return (end - start).total_seconds() / 3600.0

# 独立于 dossier.db, 默认放 backend/discovery.db; 可经 DISCOVERY_DB_PATH 覆盖 (便于测试)
_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.getenv("DISCOVERY_DB_PATH") or os.path.join(
    os.path.dirname(config.DB_PATH) if config.DB_PATH else _BACKEND,
    "discovery.db",
)


@dataclass
class ScoredItem:
    """一条带加速判定的发现项 —— 快照比对后的产物。"""
    item: DiscoveryItem
    is_new: bool                    # 本次运行才首见 = 全新苗头
    prev_signal: Optional[int]      # 上次运行时的 signal (None = 从未见过)
    delta: int                      # signal 增量 (加速量); 新项的 delta = 当前 signal
    runs_seen: int                  # 跨多少次运行被见过 (持续性)
    age_hours: Optional[float] = None  # 首次出现距本次运行多少小时 (None = 无法解析时间)


class DiscoveryStore:
    """发现快照的读写。每个实例绑定一个 db 文件。"""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS snapshot (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                source TEXT NOT NULL,
                external_id TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                signal INTEGER NOT NULL DEFAULT 0,
                engagement INTEGER NOT NULL DEFAULT 0,
                category TEXT NOT NULL DEFAULT '',
                captured_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_snapshot_key
                ON snapshot (source, external_id, captured_at);
            CREATE INDEX IF NOT EXISTS ix_snapshot_run ON snapshot (run_id);

            CREATE TABLE IF NOT EXISTS item_seen (
                source TEXT NOT NULL,
                external_id TEXT NOT NULL,
                first_seen_at TEXT NOT NULL,
                first_signal INTEGER NOT NULL DEFAULT 0,
                runs_seen INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (source, external_id)
            );
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def _prev_signal(self, source: str, external_id: str, before_run: str) -> Optional[int]:
        """同一 item 在本次运行之前、最近一次快照的 signal。None = 从未见过。"""
        row = self._conn.execute(
            """
            SELECT signal FROM snapshot
            WHERE source = ? AND external_id = ? AND run_id != ?
            ORDER BY captured_at DESC, id DESC
            LIMIT 1
            """,
            (source, external_id, before_run),
        ).fetchone()
        return int(row["signal"]) if row is not None else None

    def score(self, items: list[DiscoveryItem], run_id: str, now_iso: str) -> list[ScoredItem]:
        """对本次拉取的 items 计算加速判定 (不写库, 纯读 + 计算)。

        run_id: 本次运行的唯一标识 (调用方传入, 通常是 ISO 时间戳)。
        now_iso: 本次运行时间。注意: 计算时排除 run_id 自身, 故先 score 再 commit。
        """
        scored: list[ScoredItem] = []
        for it in items:
            prev = self._prev_signal(it.source, it.external_id, run_id)
            is_new = prev is None
            delta = it.signal if is_new else (it.signal - prev)
            seen_row = self._conn.execute(
                "SELECT runs_seen, first_seen_at FROM item_seen WHERE source = ? AND external_id = ?",
                (it.source, it.external_id),
            ).fetchone()
            runs_seen = (int(seen_row["runs_seen"]) if seen_row else 0) + 1
            # 首见距今多少小时: 已登记的用其 first_seen_at; 本次才首见的 age=0。
            first_seen = seen_row["first_seen_at"] if seen_row else now_iso
            age_hours = _hours_between(first_seen, now_iso)
            scored.append(ScoredItem(
                item=it,
                is_new=is_new,
                prev_signal=prev,
                delta=delta,
                runs_seen=runs_seen,
                age_hours=age_hours,
            ))
        return scored

    def commit_run(self, items: list[DiscoveryItem], run_id: str, now_iso: str) -> None:
        """把本次拉取写入快照, 并更新首见登记。在 score() 之后调用。"""
        for it in items:
            self._conn.execute(
                """
                INSERT INTO snapshot
                    (run_id, source, external_id, title, url, signal, engagement, category, captured_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (run_id, it.source, it.external_id, it.title, it.url,
                 it.signal, it.engagement, it.category, now_iso),
            )
            existing = self._conn.execute(
                "SELECT runs_seen FROM item_seen WHERE source = ? AND external_id = ?",
                (it.source, it.external_id),
            ).fetchone()
            if existing is None:
                self._conn.execute(
                    """
                    INSERT INTO item_seen
                        (source, external_id, first_seen_at, first_signal, runs_seen)
                    VALUES (?, ?, ?, ?, 1)
                    """,
                    (it.source, it.external_id, now_iso, it.signal),
                )
            else:
                self._conn.execute(
                    """
                    UPDATE item_seen SET runs_seen = runs_seen + 1
                    WHERE source = ? AND external_id = ?
                    """,
                    (it.source, it.external_id),
                )
        self._conn.commit()

    def run_count(self) -> int:
        """已记录的运行次数 (distinct run_id)。首次运行 = 0 -> 只能建基线。"""
        row = self._conn.execute("SELECT COUNT(DISTINCT run_id) AS n FROM snapshot").fetchone()
        return int(row["n"]) if row else 0
