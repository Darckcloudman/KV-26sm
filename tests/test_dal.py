# -*- coding: utf-8 -*-
"""
Тесты для Data Access Layer (DAL) v1.3
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock


class TestFileSystemRepository:
    """Тесты FileSystemRepository."""
    
    @pytest.fixture
    def repository(self):
        """Создать репозиторий для тестов."""
        from smp12c_vibrodiag.dal.repositories.file_system import FileSystemRepository
        return FileSystemRepository(Path("./test_data"))
    
    @pytest.mark.asyncio
    async def test_load_archive_success(self, repository):
        """Тест успешной загрузки архива."""
        # Пропускаем если нет тестовых данных
        test_file = Path("./test_data/test.rd2")
        if not test_file.exists():
            pytest.skip("Тестовые данные не найдены")
        
        result = await repository.load_archive(test_file)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_get_turbine_metrics(self, repository):
        """Тест получения метрик турбины."""
        metrics = await repository.get_turbine_metrics()
        
        # Проверка структуры
        assert 'power_kw' in metrics
        assert 'generator_speed_rpm' in metrics
        assert 'wind_speed_ms' in metrics
        assert 'cumulative_power_kwh' in metrics
    
    @pytest.mark.asyncio
    async def test_get_sensor_data(self, repository):
        """Тест получения данных датчика."""
        sensor_data = await repository.get_sensor_data(sensor_id=1)
        
        # Если данных нет (не загружен архив)
        if sensor_data is None:
            return
        
        # Проверка структуры
        assert 'sensor_id' in sensor_data
        assert 'acceleration' in sensor_data
        assert 'velocity' in sensor_data
        assert 'high_freq' in sensor_data
    
    @pytest.mark.asyncio
    async def test_get_spectrum(self, repository):
        """Тест получения спектра."""
        spectrum = await repository.get_spectrum(
            sensor_id=1,
            filter_type="HIGH"
        )
        
        # Проверка структуры
        assert 'frequencies' in spectrum
        assert 'amplitudes' in spectrum
        assert isinstance(spectrum['frequencies'], list)
        assert isinstance(spectrum['amplitudes'], list)
    
    @pytest.mark.asyncio
    async def test_get_analysis_results(self, repository):
        """Тест получения результатов анализа."""
        results = await repository.get_analysis_results(
            sensor_id=1,
            filter_type="HIGH"
        )
        
        # Проверка структуры
        assert 'rms_total' in results
        assert 'zone' in results
        assert results['zone'] in ['A', 'B', 'C', 'D']
    
    def test_list_archives(self, repository):
        """Тест получения списка архивов."""
        archives = asyncio.run(repository.list_archives())
        
        # Проверка что список возвращается
        assert isinstance(archives, list)


class TestPostgresRepository:
    """Тесты PostgresRepository (интеграционные)."""
    
    @pytest.fixture
    def skip_if_no_db(self):
        """Пропустить если БД не настроена."""
        from smp12c_vibrodiag.dal.config import settings
        if not settings.use_database:
            pytest.skip("PostgreSQL не включен (USE_DATABASE=false)")
    
    @pytest.mark.asyncio
    async def test_database_connection(self, skip_if_no_db):
        """Тест подключения к БД."""
        from smp12c_vibrodiag.dal.database import DatabaseManager
        from smp12c_vibrodiag.dal.config import settings
        
        db_manager = DatabaseManager(settings)
        connected = await db_manager.health_check()
        
        assert connected is True
        await db_manager.close()


class TestSettings:
    """Тесты конфигурации."""
    
    def test_settings_default(self):
        """Тест настроек по умолчанию."""
        from smp12c_vibrodiag.dal.config import settings
        
        assert settings.app_version == "1.3"
        assert settings.use_database is False
        assert settings.db_host == "localhost"
        assert settings.db_port == 5432
    
    def test_database_url(self):
        """Тест генерации URL подключения."""
        from smp12c_vibrodiag.dal.config import settings
        
        url = settings.database_url
        assert "postgresql+asyncpg://" in url
        assert str(settings.db_port) in url
    
    def test_database_url_sync(self):
        """Тест генерации sync URL."""
        from smp12c_vibrodiag.dal.config import settings
        
        url = settings.database_url_sync
        assert "postgresql+psycopg2://" in url


class TestRepositoryFactory:
    """Тесты фабрики репозиториев."""
    
    def test_get_file_system_repository(self):
        """Тест создания FileSystemRepository."""
        from smp12c_vibrodiag.dal.repositories.factory import get_repository
        from smp12c_vibrodiag.dal.config import settings
        from smp12c_vibrodiag.dal.repositories.file_system import FileSystemRepository
        
        # Временно отключаем БД
        original = settings.use_database
        settings.use_database = False
        
        repo = get_repository(settings)
        assert isinstance(repo, FileSystemRepository)
        
        # Возвращаем оригинальное значение
        settings.use_database = original


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
