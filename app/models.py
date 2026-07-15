from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# BIGINT on Postgres, but INTEGER on SQLite so its rowid autoincrement works.
BigIntPK = BigInteger().with_variant(Integer, "sqlite")


class Url(Base):
    __tablename__ = "urls"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    # Short alias; UNIQUE constraint is the single arbiter for collisions.
    alias: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    # The long/original URL. `Text` avoids arbitrary length caps.
    long_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    access_count: Mapped[int] = mapped_column(
        BigInteger, server_default="0", nullable=False
    )
    last_accessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
