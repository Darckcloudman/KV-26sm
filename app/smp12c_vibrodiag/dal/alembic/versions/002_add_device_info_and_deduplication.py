"""
Add device info to turbines and deduplication fields to archives

Revision ID: 002
Revises: 001
Create Date: 2025-05-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Добавить идентификаторы прибора в таблицу turbines
    и поля для дедупликации в таблицу archives.
    """
    # === Таблица turbines ===
    op.add_column('turbines', sa.Column('device', sa.String(20), nullable=True, comment='Модель устройства (например, 12C)'))
    op.add_column('turbines', sa.Column('serial_number', sa.String(50), nullable=True, comment='Серийный номер прибора (уникальный)'))
    op.add_column('turbines', sa.Column('mac_address', sa.String(17), nullable=True, comment='MAC-адрес прибора (уникальный)'))
    op.add_column('turbines', sa.Column('ip_address', sa.String(45), nullable=True, comment='IP-адрес прибора (может меняться)'))
    op.add_column('turbines', sa.Column('firmware_version', sa.String(20), nullable=True, comment='Версия прошивки прибора'))
    
    # Уникальные индексы для turbines
    op.create_index('idx_turbine_serial', 'turbines', ['serial_number'], unique=True)
    op.create_index('idx_turbine_mac', 'turbines', ['mac_address'], unique=True)
    op.create_index('idx_turbine_wtg', 'turbines', ['wtg_id'])
    
    # === Таблица archives ===
    op.add_column('archives', sa.Column('sensor_id', sa.Integer, nullable=False, server_default='1', comment='Номер датчика (1-8)'))
    op.add_column('archives', sa.Column('filter_type', sa.String(10), nullable=False, server_default='LOW', comment='Тип фильтра: FILTER, LOW, HIGH'))
    
    # Индексы для archives
    op.create_index('idx_archive_sensor', 'archives', ['sensor_id', 'filter_type'])
    
    # Уникальный составной индекс для дедупликации
    op.create_index(
        'uq_archive_unique_record',
        'archives',
        ['turbine_id', 'record_datetime', 'sensor_id', 'filter_type'],
        unique=True
    )
    
    # Убираем server_default после миграции (для новых записей будут реальные значения)
    op.alter_column('archives', 'sensor_id', server_default=None)
    op.alter_column('archives', 'filter_type', server_default=None)


def downgrade() -> None:
    """Откат изменений."""
    # Удаляем индексы archives
    op.drop_index('uq_archive_unique_record', table_name='archives')
    op.drop_index('idx_archive_sensor', table_name='archives')
    
    # Удаляем колонки archives
    op.drop_column('archives', 'sensor_id')
    op.drop_column('archives', 'filter_type')
    
    # Удаляем индексы turbines
    op.drop_index('idx_turbine_wtg', table_name='turbines')
    op.drop_index('idx_turbine_mac', table_name='turbines')
    op.drop_index('idx_turbine_serial', table_name='turbines')
    
    # Удаляем колонки turbines
    op.drop_column('turbines', 'firmware_version')
    op.drop_column('turbines', 'ip_address')
    op.drop_column('turbines', 'mac_address')
    op.drop_column('turbines', 'serial_number')
    op.drop_column('turbines', 'device')
