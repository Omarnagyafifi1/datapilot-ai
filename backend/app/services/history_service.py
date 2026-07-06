from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID, uuid4
from typing import Any

from sqlalchemy import Column, DateTime, Float, Integer, MetaData, String, Table, create_engine, select, insert, desc, func
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

_METADATA = MetaData()
_QUERY_HISTORY = Table(
    "query_history",
    _METADATA,
    Column("id", String(36), primary_key=True),
    Column("question", String(1024), nullable=False),
    Column("source_id", String(36), nullable=False),
    Column("status", String(32), nullable=False),
    Column("latency", Float, nullable=False),
    Column("has_visualization", Integer, default=0),
    Column("chart_type", String(64), nullable=True),
    Column("executed_at", DateTime, nullable=False, default=datetime.utcnow),
)

_HISTORY_ENGINE: Engine | None = None
_SESSION_FACTORY: sessionmaker | None = None

def _get_history_engine() -> Engine:
    global _HISTORY_ENGINE
    if _HISTORY_ENGINE is not None:
        return _HISTORY_ENGINE

    db_url = settings.query_history_db_url.strip()
    _HISTORY_ENGINE = create_engine(db_url, pool_pre_ping=True)
    _METADATA.create_all(_HISTORY_ENGINE, tables=[_QUERY_HISTORY])
    return _HISTORY_ENGINE

def _get_session_factory() -> sessionmaker:
    global _SESSION_FACTORY
    if _SESSION_FACTORY is None:
        _SESSION_FACTORY = sessionmaker(bind=_get_history_engine(), autoflush=False, autocommit=False)
    return _SESSION_FACTORY

class HistoryService:
    def save_query(
        self,
        question: str,
        source_id: str,
        status: str,
        latency: float,
        has_visualization: bool = False,
        chart_type: str | None = None,
    ) -> str:
        query_id = str(uuid4())
        payload = {
            "id": query_id,
            "question": question,
            "source_id": source_id,
            "status": status,
            "latency": latency,
            "has_visualization": 1 if has_visualization else 0,
            "chart_type": chart_type,
            "executed_at": datetime.utcnow(),
        }

        session_local = _get_session_factory()
        session: Session = session_local()
        try:
            session.execute(insert(_QUERY_HISTORY).values(**payload))
            session.commit()
            return query_id
        except Exception:
            session.rollback()
            logger.exception("Failed to save query history")
            return ""
        finally:
            session.close()

    def list_history(self, limit: int = 50) -> list[dict]:
        session_local = _get_session_factory()
        session: Session = session_local()
        try:
            rows = session.execute(
                select(_QUERY_HISTORY)
                .order_by(desc(_QUERY_HISTORY.c.executed_at))
                .limit(limit)
            ).mappings().all()
            return [dict(row) for row in rows]
        finally:
            session.close()

    def get_stats(self) -> dict[str, Any]:
        session_local = _get_session_factory()
        session: Session = session_local()
        try:
            total_queries = session.query(func.count(_QUERY_HISTORY.c.id)).scalar() or 0
            avg_latency = session.query(func.avg(_QUERY_HISTORY.c.latency)).scalar() or 0.0
            success_count = session.query(func.count(_QUERY_HISTORY.c.id)).filter(_QUERY_HISTORY.c.status == "SUCCESS").scalar() or 0
            viz_count = session.query(func.count(_QUERY_HISTORY.c.id)).filter(_QUERY_HISTORY.c.has_visualization == 1).scalar() or 0
            
            success_rate = (success_count / total_queries * 100) if total_queries > 0 else 0.0
            viz_rate = (viz_count / total_queries * 100) if total_queries > 0 else 0.0
            
            return {
                "total_queries": total_queries,
                "avg_latency": round(float(avg_latency), 2),
                "success_rate": round(float(success_rate), 2),
                "total_visualizations": viz_count,
                "visualization_rate": round(float(viz_rate), 2),
            }
        finally:
            session.close()

    def get_metrics(self) -> dict[str, Any]:
        stats = self.get_stats()
        trends = self.get_query_trends(days=14)
        viz_breakdown = self.get_viz_usage()
        return {
            **stats,
            "trends": trends,
            "visualization_breakdown": viz_breakdown,
        }

    def get_query_trends(self, days: int = 14) -> list[dict[str, Any]]:
        session_local = _get_session_factory()
        session: Session = session_local()
        try:
            since = datetime.utcnow() - timedelta(days=days)
            rows = session.execute(
                select(
                    func.date(_QUERY_HISTORY.c.executed_at).label("day"),
                    func.count(_QUERY_HISTORY.c.id).label("total"),
                    func.sum(func.cast(_QUERY_HISTORY.c.status == "SUCCESS", Integer)).label("success"),
                    func.sum(func.cast(_QUERY_HISTORY.c.has_visualization == 1, Integer)).label("with_viz"),
                )
                .where(_QUERY_HISTORY.c.executed_at >= since)
                .group_by(func.date(_QUERY_HISTORY.c.executed_at))
                .order_by(func.date(_QUERY_HISTORY.c.executed_at))
            ).mappings().all()

            return [
                {
                    "day": str(row["day"]),
                    "total": row["total"],
                    "success": row["success"] or 0,
                    "with_viz": row["with_viz"] or 0,
                }
                for row in rows
            ]
        finally:
            session.close()

    def get_viz_usage(self) -> list[dict[str, Any]]:
        session_local = _get_session_factory()
        session: Session = session_local()
        try:
            rows = session.execute(
                select(
                    _QUERY_HISTORY.c.chart_type,
                    func.count(_QUERY_HISTORY.c.id).label("count"),
                )
                .where(_QUERY_HISTORY.c.has_visualization == 1)
                .where(_QUERY_HISTORY.c.chart_type.isnot(None))
                .group_by(_QUERY_HISTORY.c.chart_type)
                .order_by(desc("count"))
            ).mappings().all()

            return [{"chart_type": row["chart_type"], "count": row["count"]} for row in rows]
        finally:
            session.close()

    def get_feed(self, limit: int = 10) -> list[dict]:
        # Mock some feed data combined with real history
        history = self.list_history(limit=limit)
        feed = []
        for item in history:
            feed.append({
                "id": item["id"],
                "type": "EXECUTION" if item["status"] == "SUCCESS" else "ERROR",
                "content": f"Query: {item['question'][:50]}...",
                "timestamp": item["executed_at"]
            })
        
        # Add some mock system events
        feed.append({
            "id": "sys-1",
            "type": "SYSTEM",
            "content": "Neural engine stabilized.",
            "timestamp": datetime.utcnow()
        })
        return sorted(feed, key=lambda x: x["timestamp"], reverse=True)[:limit]
