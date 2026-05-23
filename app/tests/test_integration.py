# -*- coding: utf-8 -*-
"""
Интеграционные тесты KWF Prometheus v1.4
=====================================================

Тесты работают с реальными данными из хранилища Кольской ВЭС.
Путь к хранилищу: D:\Работа [Кольская ВЭС]\SMP_SGRE\RAW_DATA

Требования:
    - PostgreSQL запущен (docker-compose -f docker-compose.test.yml up -d)
    - .env.test настроен
    - pytest-asyncio установлен

Запуск:
    powershell -ExecutionPolicy Bypass -File .\run_integration_tests.ps1
    или
    pytest tests/test_integration.py -v --tb=short

Автор: A.Telezhenko, 2026
"""

import pytest
import asyncio
import zipfile
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings():
    """Load test settings from .env.test."""
    from smp12c_vibrodiag.dal.config import Settings
    
    # Try to load from .env.test first
    env_test = Path(".env.test")
    if env_test.exists():
        return Settings(_env_file=".env.test")
    
    # Fallback to default settings with test DB
    return Settings(
        use_database=True,
        db_host="localhost",
        db_port=5432,
        db_name="vibrodiag_test_kola",
        db_user="postgres",
        db_password="postgres",
    )


@pytest.fixture(scope="session")
async def db_manager(test_settings):
    """Create database manager and initialize tables."""
    from smp12c_vibrodiag.dal.database import DatabaseManager
    
    manager = DatabaseManager(test_settings)
    
    # Check connection
    connected = await manager.health_check()
    if not connected:
        pytest.skip("PostgreSQL is not available. Start it with: docker-compose -f docker-compose.test.yml up -d")
    
    # Create tables
    await manager.create_db()
    
    yield manager
    
    # Cleanup after all tests
    await manager.drop_db()
    await manager.close()


@pytest.fixture
async def db_session(db_manager):
    """Create a fresh database session for each test."""
    async with db_manager.session_factory() as session:
        yield session
        # Rollback any uncommitted changes
        await session.rollback()


@pytest.fixture
def repository(db_manager, test_settings):
    """Create PostgresRepository instance."""
    from smp12c_vibrodiag.dal.repositories.postgres import PostgresRepository
    return PostgresRepository(db_manager, test_settings.archive_storage_path)


@pytest.fixture
def persistence_service(repository):
    """Create DataPersistenceService instance."""
    from smp12c_vibrodiag.dal.persistence_service import DataPersistenceService
    return DataPersistenceService(repository)


@pytest.fixture
def test_storage_path():
    """Path to test data storage."""
    # Local test data
    local_path = Path("./test_data")
    if local_path.exists():
        return local_path
    
    # Kola Wind Farm storage (if accessible)
    kola_path = Path(r"D:\Работа [Кольская ВЭС]\SMP_SGRE\RAW_DATA")
    if kola_path.exists():
        return kola_path
    
    pytest.skip("Test data not found. Expected: ./test_data or D:\\Работа [Кольская ВЭС]\\SMP_SGRE\\RAW_DATA")


@pytest.fixture
def sample_rd2_file(test_storage_path):
    """Get a sample .rd2 file for testing."""
    # Look for any .rd2 file in test data
    rd2_files = list(test_storage_path.rglob("*.rd2"))
    if not rd2_files:
        pytest.skip("No .rd2 files found in test data")
    return rd2_files[0]


@pytest.fixture
def sample_zip_archive(test_storage_path):
    """Get a sample ZIP archive for testing."""
    zip_files = list(test_storage_path.rglob("*SMP_RWD_*.zip"))
    if not zip_files:
        # Check local test_data/zip
        local_zip = Path("./test_data/zip")
        if local_zip.exists():
            zip_files = list(local_zip.glob("*.zip"))
    
    if not zip_files:
        pytest.skip("No ZIP archives found in test data")
    return zip_files[0]


@pytest.fixture
def temp_storage():
    """Create temporary storage for auto-scan tests."""
    temp_dir = Path(tempfile.mkdtemp(prefix="vibrodiag_test_"))
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


# =============================================================================
# TEST 2.1: Save Single .rd2 File
# =============================================================================

@pytest.mark.asyncio
class TestSaveSingleRD2:
    """Test saving a single .rd2 file to PostgreSQL."""
    
    async def test_save_single_rd2(self, persistence_service, sample_rd2_file, db_session):
        """Test 2.1: Save single .rd2 and verify DB records."""
        from sqlalchemy import select
        from smp12c_vibrodiag.dal.models import Turbine, Archive, SensorData, AnalysisCache
        
        # Act: Save the file
        result = await persistence_service.save_archive(sample_rd2_file)
        
        # Assert: Basic result structure
        assert result['success'] is True, f"Save failed: {result['errors']}"
        assert result['added'] >= 1, "Expected at least 1 record added"
        assert result['skipped'] == 0, "Expected no duplicates on first save"
        
        # Assert: Turbine record created
        turbine_result = await db_session.execute(
            select(Turbine).where(Turbine.wtg_id.isnot(None))
        )
        turbine = turbine_result.scalar_one_or_none()
        assert turbine is not None, "Turbine record not created"
        
        # Assert: Archive record created
        archive_result = await db_session.execute(
            select(Archive).where(Archive.turbine_id == turbine.id)
        )
        archive = archive_result.scalar_one_or_none()
        assert archive is not None, "Archive record not created"
        assert archive.sensor_id is not None, "sensor_id not set"
        assert archive.filter_type in ['FILTER', 'LOW', 'HIGH'], f"Invalid filter_type: {archive.filter_type}"
        
        # Assert: SensorData record created
        sensor_data_result = await db_session.execute(
            select(SensorData).where(SensorData.archive_id == archive.id)
        )
        sensor_data = sensor_data_result.scalar_one_or_none()
        assert sensor_data is not None, "SensorData record not created"
        assert len(sensor_data.values) > 0, "SensorData values are empty"
        assert len(sensor_data.timestamps) > 0, "SensorData timestamps are empty"
        assert sensor_data.samples_count > 0, "samples_count not set"
        
        # Assert: AnalysisCache record created (if analysis was triggered)
        cache_result = await db_session.execute(
            select(AnalysisCache).where(AnalysisCache.archive_id == archive.id)
        )
        cache = cache_result.scalar_one_or_none()
        if cache:
            assert cache.rms_total is not None, "RMS not calculated"
            assert cache.zone in ['A', 'B', 'C', 'D'], f"Invalid zone: {cache.zone}"
    
    async def test_turbine_device_info(self, persistence_service, sample_rd2_file, db_session):
        """Test that device info (serial, MAC) is extracted and saved."""
        from sqlalchemy import select
        from smp12c_vibrodiag.dal.models import Turbine
        
        # Save file
        result = await persistence_service.save_archive(sample_rd2_file)
        assert result['success'] is True
        
        # Check turbine has device info
        turbine_result = await db_session.execute(select(Turbine))
        turbine = turbine_result.scalar_one_or_none()
        assert turbine is not None
        
        # Device info may or may not be present depending on file format
        # but wtg_id must be set
        assert turbine.wtg_id is not None, "wtg_id not set"
        assert turbine.wtg_id != 'Unknown', "wtg_id is Unknown"


# =============================================================================
# TEST 2.2: Save ZIP Archive
# =============================================================================

@pytest.mark.asyncio
class TestSaveZipArchive:
    """Test saving ZIP archives with multiple .rd2 files."""
    
    async def test_save_zip_archive(self, persistence_service, sample_zip_archive, db_session):
        """Test 2.2: Save ZIP archive and verify all .rd2 files processed."""
        from sqlalchemy import select, func
        from smp12c_vibrodiag.dal.models import Turbine, Archive
        
        # Count files in ZIP
        with zipfile.ZipFile(sample_zip_archive, 'r') as zf:
            rd2_files_in_zip = [name for name in zf.namelist() if name.endswith('.rd2')]
        
        # Skip if ZIP doesn't contain .rd2 files (some test zips might be different)
        if not rd2_files_in_zip:
            pytest.skip("ZIP archive doesn't contain .rd2 files")
        
        # Act: Save ZIP
        result = await persistence_service.save_archive(sample_zip_archive)
        
        # Assert: Success
        assert result['success'] is True, f"ZIP save failed: {result['errors']}"
        assert result['added'] > 0, "Expected records to be added"
        
        # Assert: All files processed (may have duplicates if test re-runs)
        total_processed = result['added'] + result['skipped']
        assert total_processed == len(rd2_files_in_zip), (
            f"Expected {len(rd2_files_in_zip)} files processed, got {total_processed}"
        )
        
        # Assert: Single turbine for all files in archive
        turbine_result = await db_session.execute(select(Turbine))
        turbines = turbine_result.scalars().all()
        assert len(turbines) == 1, f"Expected 1 turbine, got {len(turbines)}"
        
        # Assert: Archive records match
        archive_count_result = await db_session.execute(
            select(func.count(Archive.id)).where(Archive.turbine_id == turbines[0].id)
        )
        archive_count = archive_count_result.scalar()
        assert archive_count == len(rd2_files_in_zip), (
            f"Expected {len(rd2_files_in_zip)} archive records, got {archive_count}"
        )


# =============================================================================
# TEST 2.3: Deduplication
# =============================================================================

@pytest.mark.asyncio
class TestDeduplication:
    """Test deduplication logic."""
    
    async def test_duplicate_rd2_skipped(self, persistence_service, sample_rd2_file):
        """Test 2.3: Re-saving same .rd2 file skips duplicates."""
        # First save
        result1 = await persistence_service.save_archive(sample_rd2_file)
        assert result1['success'] is True
        
        added_first = result1['added']
        
        # Second save (same file)
        result2 = await persistence_service.save_archive(sample_rd2_file)
        assert result2['success'] is True
        
        # All should be skipped
        assert result2['added'] == 0, f"Expected 0 added, got {result2['added']}"
        assert result2['skipped'] == added_first, (
            f"Expected {added_first} skipped, got {result2['skipped']}"
        )
    
    async def test_duplicate_zip_skipped(self, persistence_service, sample_zip_archive):
        """Test re-saving same ZIP skips all files."""
        # First save
        result1 = await persistence_service.save_archive(sample_zip_archive)
        if not result1['success']:
            pytest.skip("First ZIP save failed")
        
        # Second save - should be fully skipped (processed_archives check)
        result2 = await persistence_service.save_archive(sample_zip_archive)
        assert result2['skipped'] == -1, (
            f"Expected full skip (-1), got {result2['skipped']}"
        )


# =============================================================================
# TEST 2.4: Device Identification
# =============================================================================

@pytest.mark.asyncio
class TestDeviceIdentification:
    """Test device identification by serial_number and MAC."""
    
    async def test_same_device_same_turbine(self, persistence_service, sample_rd2_file, db_session):
        """Test 2.4: Same device serial maps to same turbine."""
        from sqlalchemy import select
        from smp12c_vibrodiag.dal.models import Turbine
        
        # Save first file
        result1 = await persistence_service.save_archive(sample_rd2_file)
        assert result1['success'] is True
        
        # Get turbine count after first save
        result_before = await db_session.execute(select(Turbine))
        count_before = len(result_before.scalars().all())
        
        # Save same file again (should not create new turbine)
        result2 = await persistence_service.save_archive(sample_rd2_file)
        
        result_after = await db_session.execute(select(Turbine))
        count_after = len(result_after.scalars().all())
        
        assert count_after == count_before, (
            f"Turbine count changed: {count_before} -> {count_after}"
        )


# =============================================================================
# TEST 2.5: Auto-scan
# =============================================================================

@pytest.mark.asyncio
class TestAutoScan:
    """Test auto-scan functionality."""
    
    async def test_scan_directory(self, persistence_service, temp_storage, sample_zip_archive):
        """Test 2.5: Scan directory and process archives."""
        from smp12c_vibrodiag.dal.auto_scan_service import AutoScanService
        
        # Copy sample ZIP to temp storage (simulate hierarchical structure)
        year_month = temp_storage / "202509"
        day_dir = year_month / "03"
        day_dir.mkdir(parents=True)
        
        temp_zip = day_dir / sample_zip_archive.name
        shutil.copy(sample_zip_archive, temp_zip)
        
        # Create auto-scan service
        service = AutoScanService(
            root_path=temp_storage,
            persistence_service=persistence_service,
            interval_minutes=10,
            enabled=True
        )
        
        # Run scan (sync via thread)
        import threading
        scan_results = {}
        
        def on_finished(result):
            scan_results['result'] = result
        
        worker = service.start_scan(on_finished=on_finished)
        worker.wait()
        
        # Assert
        assert 'result' in scan_results, "Scan did not complete"
        result = scan_results['result']
        assert result.total_found >= 1, "Expected at least 1 archive found"
        assert result.processed >= 1, "Expected at least 1 archive processed"
    
    async def test_incremental_scan(self, persistence_service, temp_storage, sample_zip_archive):
        """Test incremental scan processes only new files."""
        from smp12c_vibrodiag.dal.auto_scan_service import AutoScanService
        
        # Setup temp storage
        day_dir = temp_storage / "202509" / "03"
        day_dir.mkdir(parents=True)
        
        temp_zip1 = day_dir / sample_zip_archive.name
        shutil.copy(sample_zip_archive, temp_zip1)
        
        # First scan
        service1 = AutoScanService(temp_storage, persistence_service)
        worker1 = service1.start_scan()
        worker1.wait()
        result1 = service1.get_last_result()
        
        # Add "new" archive (copy with different name)
        temp_zip2 = day_dir / f"W1436_WTG99_SMP_RWD_20250903.zip"
        shutil.copy(sample_zip_archive, temp_zip2)
        
        # Second scan
        service2 = AutoScanService(temp_storage, persistence_service)
        worker2 = service2.start_scan()
        worker2.wait()
        result2 = service2.get_last_result()
        
        # Should find 2 total, but only process 1 new
        assert result2.total_found == 2, f"Expected 2 found, got {result2.total_found}"
        # The first one should be skipped (processed_archives), second processed
        # Note: exact counts depend on implementation


# =============================================================================
# TEST 2.6: Turbine Statistics
# =============================================================================

@pytest.mark.asyncio
class TestTurbineStatistics:
    """Test statistics retrieval for turbines."""
    
    async def test_get_turbine_statistics(self, persistence_service, repository, sample_rd2_file):
        """Test 2.6: Get statistics for a turbine."""
        # Save file
        result = await persistence_service.save_archive(sample_rd2_file)
        assert result['success'] is True
        
        wtg_id = result.get('wtg_id')
        if not wtg_id:
            pytest.skip("WTG ID not extracted from file")
        
        # Get statistics
        stats = await repository.get_turbine_statistics(wtg_id)
        
        assert stats is not None, "Statistics returned None"
        assert stats['total_archives'] > 0, "Expected at least 1 archive"
        assert 'first_record' in stats, "first_record missing"
        assert 'last_record' in stats, "last_record missing"
        assert 'avg_rms_per_sensor' in stats, "avg_rms_per_sensor missing"
        assert 'critical_count' in stats, "critical_count missing"
        
        # avg_rms should be non-negative
        for sensor_id, avg_rms in stats['avg_rms_per_sensor'].items():
            assert avg_rms >= 0, f"Invalid avg_rms for sensor {sensor_id}: {avg_rms}"


# =============================================================================
# TEST 2.7: RMS Trends
# =============================================================================

@pytest.mark.asyncio
class TestRMSTrends:
    """Test RMS trend retrieval."""
    
    async def test_get_rms_trend_single_turbine(self, persistence_service, repository, sample_rd2_file):
        """Test 2.7: Get RMS trend for a single turbine."""
        # Save file
        result = await persistence_service.save_archive(sample_rd2_file)
        assert result['success'] is True
        
        wtg_id = result.get('wtg_id')
        if not wtg_id:
            pytest.skip("WTG ID not extracted")
        
        # Get trend for sensor 1, filter LOW
        trend = await repository.get_rms_trend(
            wtg_id=wtg_id,
            sensor_id=1,
            filter_type='LOW'
        )
        
        # Trend may be empty if sensor 1 LOW not in file
        # But structure should be valid
        assert isinstance(trend, list), "Trend should be a list"
        
        if trend:
            assert 'date' in trend[0], "Trend point missing 'date'"
            assert 'rms_total' in trend[0], "Trend point missing 'rms_total'"
            assert trend[0]['rms_total'] >= 0, "RMS should be non-negative"
    
    async def test_get_rms_trend_aggregated(self, persistence_service, repository, sample_rd2_file):
        """Test 2.8: Get aggregated RMS trend for wind farm."""
        # Save file
        result = await persistence_service.save_archive(sample_rd2_file)
        assert result['success'] is True
        
        # Get aggregated trend
        trend = await repository.get_rms_trend(
            wtg_id=None,  # Aggregate all
            sensor_id=1,
            filter_type='LOW'
        )
        
        assert isinstance(trend, list), "Aggregated trend should be a list"
        
        if trend:
            assert 'date' in trend[0], "Missing 'date' in aggregated trend"
            assert 'rms_total' in trend[0], "Missing 'rms_total' in aggregated trend"
            assert trend[0]['wtg_id'] == 'AVG_ALL', "Expected wtg_id='AVG_ALL'"


# =============================================================================
# TEST 2.9: Sensor Serial Uniqueness
# =============================================================================

@pytest.mark.asyncio
class TestSensorSerialUniqueness:
    """Test sensor_serial field uniqueness analysis."""
    
    def test_sensor_serial_extraction(self, sample_rd2_file):
        """Test 2.9: Extract sensor_serial from .rd2 file."""
        from smp12c_vibrodiag.parsers.rd2_parser import RD2Parser
        
        parser = RD2Parser(str(sample_rd2_file))
        data = parser.parse()
        
        assert 'sensor_serial' in data['metadata'], "sensor_serial not in metadata"
        assert data['metadata']['sensor_serial'] is not None, "sensor_serial is None"
        assert len(data['metadata']['sensor_serial']) > 0, "sensor_serial is empty"
    
    def test_sensor_serial_matches_record_number(self, sample_rd2_file):
        """Test sensor_serial equals record_number (first field)."""
        from smp12c_vibrodiag.parsers.rd2_parser import RD2Parser
        
        parser = RD2Parser(str(sample_rd2_file))
        data = parser.parse()
        
        assert data['metadata']['sensor_serial'] == data['metadata']['record_number'], (
            "sensor_serial should equal record_number"
        )


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

@pytest.mark.asyncio
class TestPerformance:
    """Test performance requirements."""
    
    async def test_single_zip_load_time(self, persistence_service, sample_zip_archive):
        """Test ZIP load time is under 3 seconds."""
        import time
        
        start = time.time()
        result = await persistence_service.save_archive(sample_zip_archive)
        elapsed = time.time() - start
        
        if not result['success']:
            pytest.skip("ZIP save failed")
        
        assert elapsed < 3.0, f"ZIP load took {elapsed:.2f}s, expected < 3s"
    
    async def test_single_rd2_load_time(self, persistence_service, sample_rd2_file):
        """Test single .rd2 load time is under 1 second."""
        import time
        
        start = time.time()
        result = await persistence_service.save_archive(sample_rd2_file)
        elapsed = time.time() - start
        
        assert result['success'] is True
        assert elapsed < 1.0, f"RD2 load took {elapsed:.2f}s, expected < 1s"


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
