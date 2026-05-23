# -*- coding: utf-8 -*-
"""
Модель для отслеживания обработанных архивов.

Используется автопарсером для определения, какие архивы уже были
загружены в БД, а какие — новые.
"""

from datetime import datetime
from sqlalchemy import String, DateTime, Integer, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ProcessedArchive(Base):
    """
    Модель обработанного архива.
    
    Хранит информацию о каждом обработанном ZIP-архиве для
    инкрементального сканирования хранилища.
    """
    
    __tablename__ = "processed_archives"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    file_path: Mapped[str] = mapped_column(
        String(500),
        unique=True,
        nullable=False,
        index=True,
        comment="Полный путь к архиву"
    )
    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Размер файла в байтах"
    )
    file_mtime: Mapped[float] = mapped_column(
        nullable=False,
        comment="Время последней модификации файла (timestamp)"
    )
    turbine_wtg_id: Mapped[str] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="WTG ID турбины (если удалось определить)"
    )
    records_added: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Количество добавленных записей"
    )
    records_skipped: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Количество пропущенных дубликатов"
    )
    processed_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        comment="Дата обработки"
    )
    
    def __repr__(self) -> str:
        return f"<ProcessedArchive(path='{self.file_path}', added={self.records_added})>"
