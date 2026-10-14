from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import UniqueConstraint, ForeignKey

from db.base import Base


class MonthLike(Base):
    __tablename__ = "month_likes"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    month_id: Mapped[int] = mapped_column(ForeignKey("months.id"))

    __table_args__ = (UniqueConstraint("user_id", "month_id", name="uq_month_like_user_month"),)

