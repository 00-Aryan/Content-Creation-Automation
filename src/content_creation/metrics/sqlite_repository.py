"""SQLiteMetricRepository — SQLite-backed metric persistence."""

import json
import logging
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from content_creation.metrics.models import MetricRecord, MetricType
from content_creation.metrics.repository import MetricRepository
from content_creation.metrics.schema import create_metrics_schema

logger = logging.getLogger(__name__)


class SQLiteMetricRepository(MetricRepository):
    """SQLite implementation of MetricRepository.

    Thread-safe. Uses WAL mode and busy_timeout for concurrency.
    Schema initialization is idempotent.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._local = threading.local()
        self._lock = threading.Lock()
        self._all_conns = []
        self._init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a thread-local SQLite connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(
                self._db_path,
                check_same_thread=False,
                timeout=10.0,
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            self._local.conn = conn
            with self._lock:
                self._all_conns.append(conn)
        return self._local.conn

    def _init_schema(self) -> None:
        """Initialize schema on the main thread connection."""
        conn = self._get_conn()
        create_metrics_schema(conn)

    def close(self) -> None:
        """Close all database connections created by this repository."""
        with self._lock:
            conns = list(self._all_conns)
            self._all_conns.clear()
        for conn in conns:
            try:
                conn.close()
            except Exception:
                logger.debug("Error closing metrics store connection")
        if hasattr(self._local, "conn"):
            self._local.conn = None

    def _row_to_record(self, row: sqlite3.Row) -> MetricRecord:
        """Convert a SQLite row to a MetricRecord."""
        dimensions = {}
        try:
            dimensions = json.loads(row["dimensions_json"]) if row["dimensions_json"] else {}
        except (json.JSONDecodeError, TypeError):
            pass

        return MetricRecord(
            metric_id=UUID(row["id"]),
            metric_name=row["metric_name"],
            metric_type=MetricType(row["metric_type"]),
            value=row["value"],
            timestamp=datetime.fromisoformat(row["created_at"]),
            entity_type=row["entity_type"],
            entity_id=row["entity_id"],
            dimensions=dimensions,
        )

    def save_metric(self, record: MetricRecord) -> None:
        """Persist a metric record. Idempotent on duplicate metric_id."""
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT OR IGNORE INTO metrics
                   (id, metric_name, metric_type, value, created_at,
                    entity_type, entity_id, dimensions_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(record.metric_id),
                    record.metric_name,
                    record.metric_type.value,
                    record.value,
                    record.timestamp.isoformat(),
                    record.entity_type,
                    record.entity_id,
                    json.dumps(record.dimensions, default=str),
                ),
            )
            conn.commit()
            logger.debug("Saved metric %s (%s)", record.metric_id, record.metric_name)
        except sqlite3.Error:
            logger.exception("Failed to save metric %s", record.metric_id)
            conn.rollback()
            raise

    def get_metric(self, metric_id: UUID) -> Optional[MetricRecord]:
        """Retrieve a single metric by ID."""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT * FROM metrics WHERE id = ?", (str(metric_id),)
        )
        row = cursor.fetchone()
        return self._row_to_record(row) if row else None

    def query_metrics(
        self,
        metric_name: Optional[str] = None,
        metric_type: Optional[MetricType] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        dimensions: Optional[Dict[str, str]] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[MetricRecord]:
        """Query metrics with flexible filtering."""
        conn = self._get_conn()
        conditions: List[str] = []
        params: List = []

        if metric_name:
            conditions.append("metric_name = ?")
            params.append(metric_name)
        if metric_type:
            conditions.append("metric_type = ?")
            params.append(metric_type.value)
        if entity_type:
            conditions.append("entity_type = ?")
            params.append(entity_type)
        if entity_id:
            conditions.append("entity_id = ?")
            params.append(entity_id)
        if start:
            conditions.append("created_at >= ?")
            params.append(start.isoformat())
        if end:
            conditions.append("created_at <= ?")
            params.append(end.isoformat())

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT * FROM metrics WHERE {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = conn.execute(query, params)
        records = [self._row_to_record(row) for row in cursor.fetchall()]

        if dimensions:
            records = [
                r for r in records
                if all(r.dimensions.get(k) == v for k, v in dimensions.items())
            ]

        return records

    def aggregate_metrics(
        self,
        metric_name: str,
        aggregation: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        entity_type: Optional[str] = None,
        dimensions: Optional[Dict[str, str]] = None,
    ) -> Optional[float]:
        """Aggregate metrics by name and operation."""
        conn = self._get_conn()
        conditions: List[str] = ["metric_name = ?"]
        params: List = [metric_name]

        if start:
            conditions.append("created_at >= ?")
            params.append(start.isoformat())
        if end:
            conditions.append("created_at <= ?")
            params.append(end.isoformat())
        if entity_type:
            conditions.append("entity_type = ?")
            params.append(entity_type)

        where_clause = " AND ".join(conditions)

        agg_func = aggregation.lower()
        if agg_func not in ("sum", "avg", "min", "max", "count"):
            raise ValueError(f"Unsupported aggregation: {aggregation}")

        sql_agg = "COUNT(*)" if agg_func == "count" else f"{agg_func.upper()}(value)"
        query = f"SELECT {sql_agg} FROM metrics WHERE {where_clause}"

        cursor = conn.execute(query, params)
        result = cursor.fetchone()[0]

        if dimensions and result is not None and agg_func != "count":
            records = self.query_metrics(
                metric_name=metric_name, start=start, end=end,
                entity_type=entity_type, limit=10000,
            )
            filtered = [
                r for r in records
                if all(r.dimensions.get(k) == v for k, v in dimensions.items())
            ]
            if not filtered:
                return None
            values = [r.value for r in filtered]
            if agg_func == "sum":
                return sum(values)
            elif agg_func == "avg":
                return sum(values) / len(values)
            elif agg_func == "min":
                return min(values)
            elif agg_func == "max":
                return max(values)
            return float(len(filtered))

        return float(result) if result is not None else None

    def aggregate_by_dimensions(
        self,
        metric_name: str,
        aggregation: str,
        dimension_key: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, float]:
        """Aggregate metrics grouped by a dimension key."""
        records = self.query_metrics(
            metric_name=metric_name, start=start, end=end, limit=10000,
        )

        groups: Dict[str, List[float]] = {}
        for r in records:
            dim_value = r.dimensions.get(dimension_key, "unknown")
            groups.setdefault(dim_value, []).append(r.value)

        results: Dict[str, float] = {}
        agg_func = aggregation.lower()
        for dim_val, values in groups.items():
            if agg_func == "sum":
                results[dim_val] = sum(values)
            elif agg_func == "avg":
                results[dim_val] = sum(values) / len(values) if values else 0.0
            elif agg_func == "min":
                results[dim_val] = min(values) if values else 0.0
            elif agg_func == "max":
                results[dim_val] = max(values) if values else 0.0
            elif agg_func == "count":
                results[dim_val] = float(len(values))
            else:
                raise ValueError(f"Unsupported aggregation: {aggregation}")

        return results

    def count_metrics(
        self,
        metric_name: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> int:
        """Count total metrics matching filters."""
        conn = self._get_conn()
        conditions: List[str] = []
        params: List = []

        if metric_name:
            conditions.append("metric_name = ?")
            params.append(metric_name)
        if start:
            conditions.append("created_at >= ?")
            params.append(start.isoformat())
        if end:
            conditions.append("created_at <= ?")
            params.append(end.isoformat())

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT COUNT(*) FROM metrics WHERE {where_clause}"

        cursor = conn.execute(query, params)
        return cursor.fetchone()[0]

    def delete_expired(self, before: datetime) -> int:
        """Delete metrics older than the given timestamp. Returns count deleted."""
        conn = self._get_conn()
        cursor = conn.execute(
            "DELETE FROM metrics WHERE created_at < ?",
            (before.isoformat(),),
        )
        conn.commit()
        deleted = cursor.rowcount
        if deleted > 0:
            logger.info("Deleted %d expired metrics before %s", deleted, before.isoformat())
        return deleted
