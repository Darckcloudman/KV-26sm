# -*- coding: utf-8 -*-
"""
Базовый класс для моделей SQLAlchemy.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Базовый класс для всех моделей ORM."""
    pass
