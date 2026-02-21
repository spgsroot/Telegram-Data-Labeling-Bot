from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, SmallInteger, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)

    labels: Mapped[list["Label"]] = relationship(back_populates="user")


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    text_hash: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)

    labels: Mapped[list["Label"]] = relationship(back_populates="item")


class Label(Base):
    __tablename__ = "labels"

    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), primary_key=True)
    score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    item: Mapped["Item"] = relationship(back_populates="labels")
    user: Mapped["User"] = relationship(back_populates="labels")
