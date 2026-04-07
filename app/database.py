"""SQLAlchemy database setup for HP Police ReportStream."""

import os
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, String, Float, DateTime, Text, JSON, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./phq_reports.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Report(Base):
    """Report database model."""
    __tablename__ = "reports"

    id = Column(String, primary_key=True, index=True)
    unit_name = Column(String, default="")
    reserves_deployed = Column(String, default="")
    districts = Column(String, default="")
    stay_arrangement = Column(String, default="")
    messing = Column(String, default="")
    co_interaction_date = Column(String, default="")
    disciplinary_issues = Column(String, default="")
    reserves_detained = Column(String, default="")
    training = Column(String, default="")
    welfare = Column(String, default="")
    reserves_available = Column(String, default="")
    issues_for_phq = Column(String, default="")
    
    confidence_scores = Column(JSON, default=dict)
    detected_format = Column(String, default="unknown")
    raw_input = Column(Text, default="")
    
    processing_time = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_report(db: Session, report_data: dict) -> Report:
    """Save or update a report."""
    report = Report(**report_data)
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_report(db: Session, report_id: str) -> Optional[Report]:
    """Get report by ID."""
    return db.query(Report).filter(Report.id == report_id).first()


def get_all_reports(db: Session, skip: int = 0, limit: int = 100) -> list[Report]:
    """Get all reports with pagination."""
    return db.query(Report).order_by(Report.created_at.desc()).offset(skip).limit(limit).all()


def delete_report(db: Session, report_id: str) -> bool:
    """Delete a report."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if report:
        db.delete(report)
        db.commit()
        return True
    return False


def get_reports_count(db: Session) -> int:
    """Get total count of reports."""
    return db.query(Report).count()


def get_reports_count_simple() -> int:
    """Get total count of reports (convenience function for desktop)."""
    db = SessionLocal()
    try:
        return db.query(Report).count()
    finally:
        db.close()


def get_all_reports_simple(skip: int = 0, limit: int = 100) -> list:
    """Get all reports (convenience function for desktop)."""
    db = SessionLocal()
    try:
        return db.query(Report).order_by(Report.created_at.desc()).offset(skip).limit(limit).all()
    finally:
        db.close()


def save_report_simple(report_data: dict) -> Report:
    """Save or update a report (convenience function for desktop)."""
    db = SessionLocal()
    try:
        report = Report(**report_data)
        db.add(report)
        db.commit()
        db.refresh(report)
        return report
    finally:
        db.close()


def delete_report_simple(report_id: str) -> bool:
    """Delete a report (convenience function for desktop)."""
    db = SessionLocal()
    try:
        report = db.query(Report).filter(Report.id == report_id).first()
        if report:
            db.delete(report)
            db.commit()
            return True
        return False
    finally:
        db.close()


def get_reports_in_date_range(db: Session, start_date: datetime, end_date: datetime) -> list[Report]:
    """Get reports within date range."""
    return db.query(Report).filter(
        Report.created_at >= start_date,
        Report.created_at <= end_date
    ).order_by(Report.created_at.desc()).all()


def get_field_statistics(db: Session) -> dict:
    """Get per-field statistics."""
    reports = db.query(Report).all()
    
    field_stats = {}
    fields = [
        "unit_name", "reserves_deployed", "districts", "stay_arrangement",
        "messing", "co_interaction_date", "disciplinary_issues",
        "reserves_detained", "training", "welfare", "reserves_available", "issues_for_phq"
    ]
    
    for field in fields:
        filled = sum(1 for r in reports if getattr(r, field, None))
        total = len(reports)
        avg_conf = 0
        if reports:
            confs = [r.confidence_scores.get(field, 0) for r in reports if r.confidence_scores]
            avg_conf = sum(confs) / len(confs) if confs else 0
        
        field_stats[field] = {
            "filled": filled,
            "total": total,
            "fill_rate": filled / total if total > 0 else 0,
            "avg_confidence": round(avg_conf, 3)
        }
    
    return field_stats


def get_trend_data(db: Session, days: int = 7) -> dict:
    """Get trend data for specified days."""
    from datetime import timedelta
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    reports = get_reports_in_date_range(db, start_date, end_date)
    
    daily_stats = {}
    for report in reports:
        day = report.created_at.date().isoformat()
        if day not in daily_stats:
            daily_stats[day] = {"count": 0, "total_confidence": 0, "processing_time": 0}
        
        daily_stats[day]["count"] += 1
        if report.confidence_scores:
            avg_conf = sum(report.confidence_scores.values()) / len(report.confidence_scores)
            daily_stats[day]["total_confidence"] += avg_conf
        daily_stats[day]["processing_time"] += report.processing_time
    
    result = []
    for day, stats in sorted(daily_stats.items()):
        count = stats["count"]
        result.append({
            "date": day,
            "count": count,
            "avg_confidence": round(stats["total_confidence"] / count, 3) if count > 0 else 0,
            "avg_processing_time": round(stats["processing_time"] / count, 3) if count > 0 else 0
        })
    
    return result


def search_reports_simple(keyword: str, limit: int = 100) -> list:
    """Search reports by keyword (convenience function for desktop)."""
    db = SessionLocal()
    try:
        keyword_lower = f"%{keyword.lower()}%"
        return db.query(Report).filter(
            (Report.unit_name.ilike(keyword_lower)) |
            (Report.districts.ilike(keyword_lower)) |
            (Report.reserves_deployed.ilike(keyword_lower)) |
            (Report.raw_input.ilike(keyword_lower))
        ).order_by(Report.created_at.desc()).limit(limit).all()
    finally:
        db.close()


def filter_reports_simple(
    district: str = None,
    date_from: datetime = None,
    date_to: datetime = None,
    min_confidence: float = None,
    limit: int = 100
) -> list:
    """Filter reports by various criteria (convenience function for desktop)."""
    db = SessionLocal()
    try:
        query = db.query(Report)
        
        if district:
            query = query.filter(Report.districts.ilike(f"%{district}%"))
        
        if date_from:
            query = query.filter(Report.created_at >= date_from)
        
        if date_to:
            query = query.filter(Report.created_at <= date_to)
        
        results = query.order_by(Report.created_at.desc()).limit(limit).all()
        
        if min_confidence is not None:
            filtered = []
            for r in results:
                if r.confidence_scores:
                    avg_conf = sum(r.confidence_scores.values()) / len(r.confidence_scores)
                    if avg_conf >= min_confidence:
                        filtered.append(r)
            return filtered
        
        return results
    finally:
        db.close()