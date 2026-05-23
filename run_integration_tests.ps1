# KWF Prometheus - Integration Tests Runner
# Best practice: run via powershell.exe -ExecutionPolicy Bypass -File .\run_integration_tests.ps1

Write-Host "=== KWF Prometheus - Integration Tests ===" -ForegroundColor Cyan
Write-Host ""

# Check Docker
Write-Host "1. Checking Docker..." -ForegroundColor Yellow
$dockerVersion = docker --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "   Error: Docker not found. Please install Docker Desktop." -ForegroundColor Red
    Write-Host "   Then run: docker-compose -f docker-compose.test.yml up -d" -ForegroundColor Yellow
    exit 1
}
Write-Host "   Docker: $dockerVersion" -ForegroundColor Green

# Start PostgreSQL
Write-Host ""
Write-Host "2. Starting PostgreSQL test container..." -ForegroundColor Yellow
docker-compose -f docker-compose.test.yml up -d
Start-Sleep -Seconds 5

# Wait for PostgreSQL to be ready
Write-Host "   Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
$retryCount = 0
$maxRetries = 10
while ($retryCount -lt $maxRetries) {
    $result = docker exec vibrodiag-postgres-test pg_isready -U postgres 2>&1
    if ($result -like "*accepting connections*") {
        Write-Host "   PostgreSQL is ready!" -ForegroundColor Green
        break
    }
    $retryCount++
    Start-Sleep -Seconds 2
}

if ($retryCount -eq $maxRetries) {
    Write-Host "   Error: PostgreSQL failed to start" -ForegroundColor Red
    exit 1
}

# Run migrations
Write-Host ""
Write-Host "3. Running Alembic migrations..." -ForegroundColor Yellow
$env:PYTHONPATH = "."
alembic -c smp12c_vibrodiag/dal/alembic.ini upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Host "   Error: Migration failed" -ForegroundColor Red
    exit 1
}
Write-Host "   Migrations completed" -ForegroundColor Green

# Run tests
Write-Host ""
Write-Host "4. Running integration tests..." -ForegroundColor Yellow
Write-Host ""

$env:PYTHONPATH = "."
$env:ENV_FILE = ".env.test"
python -m pytest tests/test_integration.py -v --tb=short

$testResult = $LASTEXITCODE

# Cleanup (optional)
Write-Host ""
Write-Host "5. Cleanup..." -ForegroundColor Yellow
Write-Host "   PostgreSQL container is still running. To stop:" -ForegroundColor Gray
Write-Host "   docker-compose -f docker-compose.test.yml down" -ForegroundColor Cyan

if ($testResult -eq 0) {
    Write-Host ""
    Write-Host "=== All tests passed! ===" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "=== Some tests failed ===" -ForegroundColor Red
}

exit $testResult
