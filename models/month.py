from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, text, ForeignKey, Index, String, func, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base



class Month(Base):
    __tablename__ = "months"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(30))
    norm_temp: Mapped[int | None] = mapped_column(SmallInteger)
    norm_precip: Mapped[int | None] = mapped_column(SmallInteger)
    description: Mapped[str | None] = mapped_column(String(1000))
    image_url: Mapped[str] = mapped_column(String(200))
    video_url: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), server_default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    formed_at: Mapped[datetime | None] = mapped_column(DateTime)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'published', 'deleted')", name="ck_month_status"),
        Index("uq_months_one_draft_per_creator",
              "creator_id",
              unique=True,
              postgresql_where=text("status = 'draft'"),
        ),
    )
    