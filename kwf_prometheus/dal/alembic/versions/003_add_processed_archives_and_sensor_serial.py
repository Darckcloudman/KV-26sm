"""
Add processed_archives table and sensor_serial to archives

Revision ID: 003
Revises: 002
Create Date: 2025-06-01
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Добавить:
    1. Таблицу processed_archives для отслеживания обработанных ZIP-архивов.
    2. Колонку sensor_serial в archives (для будущего анализа уникальности).
    """
    # === Таблица processed_archives ===
    op.create_table(
        'processed_archives',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('file_path', sa.String(500), nullable=False, comment='Полный путь к архиву'),
        sa.Column('file_size', sa.BigInteger, nullable=False, comment='Размер файла в байтах'),
        sa.Column('file_mtime', sa.Float, nullable=False, comment='Время последней модификации файла (timestamp)'),
        sa.Column('turbine_wtg_id', sa.String(50), nullable=True, comment='WTG ID турбины (если удалось определить)'),
        sa.Column('records_added', sa.Integer, nullable=False, server_default='0', comment='Количество добавленных записей'),
        sa.Column('records_skipped', sa.Integer, nullable=False, server_default='0', comment='Количество пропущенных дубликатов'),
        sa.Column('processed_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()'), comment='Дата обработки'),
    )
    
    # Уникальный индекс по пути
    op.create_index('idx_processed_path', 'processed_archives', ['file_path'], unique=True)
    # Индекс по WTG для быстрого поиска
    op.create_index('idx_processed_wtg', 'processed_archives', ['turbine_wtg_id'])
    
    # === Колонка sensor_serial в archives ===
    # sensor_serial = record_number (первое поле строки 1 .rd2).
    # Это порядковый номер записи за сутки для ВЭУ. Все .rd2 файлы
    # внутри одного ZIP-архива имеют ОДИНАКОВОЕ значение.
    # Используется только как информационное поле (аудит).
    op.add_column(
        'archives',
        sa.Column('sensor_serial', sa.String(50), nullable=True, comment='Порядковый номер записи за сутки (record_number). Информационное поле, НЕ для дедупликации.')
    )
    op.create_index('idx_archive_sensor_serial', 'archives', ['sensor_serial'])
    
    # Убираем server_default для processed_archives
    op.alter_column('processed_archives', 'records_added', server_default=None)
    op.alter_column('processed_archives', 'records_skipped', server_default=None)
    op.alter_column('processed_archives', 'processed_at', server_default=None)


def downgrade() -> None:
    """Откат изменений."""
    # Удаляем колонку sensor_serial
    op.drop_index('idx_archive_sensor_serial', table_name='archives')
    op.drop_column('archives', 'sensor_serial')
    
    # Удаляем таблицу processed_archives
    op.drop_index('idx_processed_wtg', table_name='processed_archives')
    op.drop_index('idx_processed_path', table_name='processed_archives')
    op.drop_table('processed_archives')
