# -*- coding: utf-8 -*-
"""
Добавление маппинга датчиков к компонентам (редуктор/генератор).

Revision ID: 004
Revises: 003
Create Date: 2025-01-28

Датчики 1-5: Редуктор (Gearbox)
Датчики 6-8: Генератор (Generator)
"""

from typing import cast
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Inspector


revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Создаём тип ENUM для компонент
    try:
        op.execute("""
            CREATE TYPE component_type AS ENUM ('gearbox', 'generator', 'other')
        """)
    except Exception:
        # Тип уже существует, пропускаем
        pass
    
    # Получаем инспектор БД для проверки существующих объектов
    conn = op.get_context().bind
    inspector = cast(Inspector, sa.inspect(conn))
    
    # Проверяем существование таблицы sensors
    if not inspector.has_table('sensors'):  # type: ignore
        # Создаём таблицу sensors с component_type
        op.create_table(
            'sensors',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('turbine_id', sa.Integer(), nullable=False),
            sa.Column('position_code', sa.Integer(), nullable=False),
            sa.Column('description', sa.String(length=200), nullable=True),
            sa.Column('component_type', sa.Enum('gearbox', 'generator', 'other', name='component_type'), nullable=False),
            sa.Column('sensor_type', sa.String(length=50), nullable=True),
            sa.Column('frequency_range_low', sa.Float(), nullable=True),
            sa.Column('frequency_range_high', sa.Float(), nullable=True),
            sa.Column('is_active', sa.Boolean(), default=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['turbine_id'], ['turbines.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('turbine_id', 'position_code')
        )
        op.create_index('idx_sensors_turbine_position', 'sensors', ['turbine_id', 'position_code'], unique=True)
        op.create_index('idx_sensors_component', 'sensors', ['component_type', 'position_code'], unique=False)
    else:
        # Добавляем колонку component_type в существующую таблицу
        if not inspector.has_column('sensors', 'component_type'):  # type: ignore
            op.add_column('sensors', sa.Column(
                'component_type',
                sa.Enum('gearbox', 'generator', 'other', name='component_type'),
                nullable=True
            ))
        
        # Устанавливаем значения по умолчанию на основе position_code
        op.execute("""
            UPDATE sensors 
            SET component_type = 'gearbox' 
            WHERE position_code BETWEEN 1 AND 5 AND component_type IS NULL
        """)
        
        op.execute("""
            UPDATE sensors 
            SET component_type = 'generator' 
            WHERE position_code BETWEEN 6 AND 8 AND component_type IS NULL
        """)
        
        # Делаем колонку NOT NULL
        op.execute("""
            UPDATE sensors SET component_type = 'other' WHERE component_type IS NULL
        """)
        op.alter_column('sensors', 'component_type', nullable=False)
        
        # Создаём индекс
        if not inspector.has_index('sensors', 'idx_sensors_component'):  # type: ignore
            op.create_index(
                'idx_sensors_component',
                'sensors',
                ['component_type', 'position_code']
            )
    
    # Создаём таблицу конфигураций датчиков (если не существует)
    if not inspector.has_table('sensor_configurations'):  # type: ignore
        op.create_table(
            'sensor_configurations',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('turbine_model', sa.String(length=50), nullable=False),
            sa.Column('position_code', sa.Integer(), nullable=False),
            sa.Column('component_type', sa.Enum('gearbox', 'generator', 'other', name='component_type'), nullable=False),
            sa.Column('description', sa.String(length=200), nullable=True),
            sa.Column('sensor_type', sa.String(length=50), nullable=True),
            sa.Column('frequency_range_low', sa.Float(), nullable=True),
            sa.Column('frequency_range_high', sa.Float(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('turbine_model', 'position_code')
        )
        
        # Вставляем стандартную конфигурацию для датчиков
        default_configs = [
            # Редуктор (датчики 1-5)
            (1, 'gearbox', 'Главный вал (радиальный)', 'acceleration', 0.1, 10.0),
            (2, 'gearbox', 'Редуктор вход (осевой)', 'acceleration', 0.1, 10.0),
            (3, 'gearbox', 'Редуктор промежуточная ступень', 'acceleration', 10.0, 1000.0),
            (4, 'gearbox', 'Редуктор выход (радиальный)', 'acceleration', 10.0, 1000.0),
            (5, 'gearbox', 'Редуктор выход (осевой)', 'acceleration', 10.0, 1000.0),
            # Генератор (датчики 6-8)
            (6, 'generator', 'Генератор DE (радиальный)', 'acceleration', 10.0, 1000.0),
            (7, 'generator', 'Генератор NDE (радиальный)', 'acceleration', 10.0, 1000.0),
            (8, 'generator', 'Генератор (осевой)', 'acceleration', 0.1, 10.0),
        ]
        
        for pos, comp_type, desc, sens_type, freq_low, freq_high in default_configs:
            op.execute(f"""
                INSERT INTO sensor_configurations 
                (turbine_model, position_code, component_type, description, sensor_type, frequency_range_low, frequency_range_high)
                VALUES ('DEFAULT', {pos}, '{comp_type}', '{desc}', '{sens_type}', {freq_low}, {freq_high})
            """)


def downgrade() -> None:
    # Удаляем таблицу конфигураций
    op.drop_table('sensor_configurations')
    
    # Удаляем индекс и колонку
    op.drop_index('idx_sensors_component', table_name='sensors')
    op.drop_column('sensors', 'component_type')
    
    # Удаляем тип ENUM (если не используется другими таблицами)
    try:
        op.execute("DROP TYPE component_type")
    except Exception:
        pass
