"""SQLite implementation of the NotificationRepository interface."""

import sqlite3
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from content_creation.notifications.models import (
    Notification,
    NotificationCategory,
    NotificationSeverity,
    NotificationStatus,
)
from content_creation.notifications.repository import NotificationRepository


class SQLiteNotificationRepository(NotificationRepository):
    """SQLite notification repository handling persistence and querying."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def _to_model(self, row: tuple) -> Notification:
        """Map a database row to a Notification domain model."""
        (
            notification_id,
            title,
            message,
            severity,
            category,
            status,
            timestamp,
            correlation_id,
            event_id,
            entity_type,
            entity_id,
        ) = row

        return Notification(
            notification_id=UUID(notification_id),
            title=title,
            message=message,
            severity=NotificationSeverity(severity),
            category=NotificationCategory(category),
            status=NotificationStatus(status),
            timestamp=datetime.fromisoformat(timestamp),
            correlation_id=correlation_id,
            event_id=UUID(event_id) if event_id else None,
            entity_type=entity_type,
            entity_id=entity_id,
        )

    def _to_row(self, notification: Notification) -> tuple:
        """Map a Notification domain model to a database row tuple."""
        return (
            str(notification.notification_id),
            notification.title,
            notification.message,
            notification.severity.value,
            notification.category.value,
            notification.status.value,
            notification.timestamp.isoformat(),
            notification.correlation_id,
            str(notification.event_id) if notification.event_id else None,
            notification.entity_type,
            notification.entity_id,
        )

    def create_notification(self, notification: Notification) -> None:
        cursor = self.conn.cursor()
        row = self._to_row(notification)
        try:
            cursor.execute(
                """
                INSERT INTO notifications (
                    notification_id, title, message, severity, category,
                    status, timestamp, correlation_id, event_id,
                    entity_type, entity_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                row,
            )
            self.conn.commit()
        except sqlite3.IntegrityError as e:
            self.conn.rollback()
            raise ValueError(
                f"Notification with ID {notification.notification_id} already exists: {e}"
            )

    def get_notification(self, notification_id: UUID) -> Optional[Notification]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM notifications WHERE notification_id = ?",
            (str(notification_id),),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self._to_model(row)

    def list_notifications(
        self,
        status: Optional[NotificationStatus] = None,
        category: Optional[NotificationCategory] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Notification]:
        cursor = self.conn.cursor()
        query = "SELECT * FROM notifications WHERE 1=1"
        params: list = []
        if status is not None:
            query += " AND status = ?"
            params.append(status.value)
        if category is not None:
            query += " AND category = ?"
            params.append(category.value)
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [self._to_model(row) for row in rows]

    def unread_count(self) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM notifications WHERE status = 'UNREAD'"
        )
        return cursor.fetchone()[0]

    def mark_read(self, notification_id: UUID) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE notifications
            SET status = ?
            WHERE notification_id = ? AND status != 'ARCHIVED'
            """,
            (NotificationStatus.READ.value, str(notification_id)),
        )
        self.conn.commit()

    def archive(self, notification_id: UUID) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE notifications
            SET status = ?
            WHERE notification_id = ?
            """,
            (NotificationStatus.ARCHIVED.value, str(notification_id)),
        )
        self.conn.commit()

    def cleanup_expired_notifications(self, max_age_seconds: int) -> int:
        cursor = self.conn.cursor()
        now = datetime.now(timezone.utc)
        cutoff = now.timestamp() - max_age_seconds
        cutoff_dt = datetime.fromtimestamp(cutoff, tz=timezone.utc)
        cutoff_iso = cutoff_dt.isoformat()

        cursor.execute(
            """
            DELETE FROM notifications
            WHERE status IN ('READ', 'ARCHIVED')
              AND timestamp < ?
            """,
            (cutoff_iso,),
        )
        deleted = cursor.rowcount
        self.conn.commit()
        return deleted
