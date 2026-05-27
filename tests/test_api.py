"""
Integration tests for FairPrice Watchdog API
"""
import pytest
import uuid
from datetime import datetime
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import AsyncSessionLocal, Base, engine
from app.models.scan import Scan
from app.models.listing import Listing
from app.models.fee import Fee
from app.models.evidence_snapshot import EvidenceSnapshot


@pytest.fixture(scope="function")
async def db_session():
    """Create a fresh database session for each test"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    """Create an async HTTP client for testing"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def sample_scan(db_session):
    """Create a sample scan with listings, fees, and evidence snapshots"""
    # Create scan
    scan = Scan(
        id=uuid.uuid4(),
        url="https://example.com/product",
        status="completed"
    )
    db_session.add(scan)
    await db_session.flush()
    
    # Create listings
    listing1 = Listing(
        id=uuid.uuid4(),
        scan_id=scan.id,
        advertised_price=100.0,
        final_price=125.0,
        location_state="california"
    )
    listing2 = Listing(
        id=uuid.uuid4(),
        scan_id=scan.id,
        advertised_price=100.0,
        final_price=130.0,
        location_state="texas"
    )
    db_session.add(listing1)
    db_session.add(listing2)
    await db_session.flush()
    
    # Create fees
    fee1 = Fee(
        id=uuid.uuid4(),
        listing_id=listing1.id,
        fee_name="Service Fee",
        fee_amount=15.0,
        fee_type="service",
        is_junk_fee=True,
        ftc_clause="16 CFR 310.3(a)(2)"
    )
    fee2 = Fee(
        id=uuid.uuid4(),
        listing_id=listing1.id,
        fee_name="Processing Fee",
        fee_amount=10.0,
        fee_type="processing",
        is_junk_fee=True,
        ftc_clause="16 CFR 310.3(a)(2)"
    )
    fee3 = Fee(
        id=uuid.uuid4(),
        listing_id=listing2.id,
        fee_name="Delivery Fee",
        fee_amount=30.0,
        fee_type="delivery",
        is_junk_fee=False,
        ftc_clause=None
    )
    db_session.add(fee1)
    db_session.add(fee2)
    db_session.add(fee3)
    await db_session.flush()
    
    # Create evidence snapshots
    snapshot1 = EvidenceSnapshot(
        id=uuid.uuid4(),
        scan_id=scan.id,
        html_content="<html><body>Evidence 1</body></html>",
        sha256_hash="abc123def456",
        timestamp=datetime.utcnow()
    )
    snapshot2 = EvidenceSnapshot(
        id=uuid.uuid4(),
        scan_id=scan.id,
        html_content="<html><body>Evidence 2</body></html>",
        sha256_hash="xyz789uvw012",
        timestamp=datetime.utcnow()
    )
    db_session.add(snapshot1)
    db_session.add(snapshot2)
    
    await db_session.commit()
    await db_session.refresh(scan)
    
    return scan


@pytest.mark.asyncio
async def test_health_check(client):
    """Test GET /health returns 200"""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_create_scan(client):
    """Test POST /scan with valid URL returns scan_id"""
    scan_data = {
        "url": "https://example.com/product",
        "geos": ["california", "texas"]
    }
    
    response = await client.post("/api/scan", json=scan_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "id" in data
    assert data["url"] == scan_data["url"]
    assert data["status"] == "queued"
    assert data["geos"] == scan_data["geos"]
    
    # Verify UUID format
    try:
        uuid.UUID(data["id"])
    except ValueError:
        pytest.fail("Invalid UUID format")


@pytest.mark.asyncio
async def test_get_scan(client, sample_scan):
    """Test GET /scan/{scan_id} returns scan"""
    response = await client.get(f"/api/scan/{sample_scan.id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == str(sample_scan.id)
    assert data["url"] == sample_scan.url
    assert data["status"] == sample_scan.status
    assert "created_at" in data
    assert "geos" in data


@pytest.mark.asyncio
async def test_get_scan_not_found(client):
    """Test GET /scan/{scan_id} with non-existent scan returns 404"""
    fake_id = uuid.uuid4()
    response = await client.get(f"/api/scan/{fake_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_results(client, sample_scan):
    """Test GET /results/{scan_id} returns results"""
    response = await client.get(f"/api/results/{sample_scan.id}")
    assert response.status_code == 200
    
    data = response.json()
    assert "scan" in data
    assert "listings" in data
    
    # Verify scan data
    assert data["scan"]["id"] == str(sample_scan.id)
    assert data["scan"]["url"] == sample_scan.url
    
    # Verify listings
    assert len(data["listings"]) == 2
    
    # Verify fees in listings
    listing_with_fees = [l for l in data["listings"] if len(l["fees"]) > 1][0]
    assert len(listing_with_fees["fees"]) == 2
    
    # Verify fee structure
    fee = listing_with_fees["fees"][0]
    assert "id" in fee
    assert "fee_name" in fee
    assert "fee_amount" in fee
    assert "fee_type" in fee
    assert "is_junk_fee" in fee


@pytest.mark.asyncio
async def test_get_results_not_found(client):
    """Test GET /results/{scan_id} with non-existent scan returns 404"""
    fake_id = uuid.uuid4()
    response = await client.get(f"/api/results/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_complaint(client, sample_scan):
    """Test POST /generate-complaint/{scan_id} returns ZIP"""
    response = await client.post(f"/api/generate-complaint/{sample_scan.id}")
    assert response.status_code == 200
    
    # Verify response is a ZIP file
    assert response.headers["content-type"] == "application/zip"
    assert "attachment" in response.headers["content-disposition"]
    assert f"evidence_bundle_{sample_scan.id}.zip" in response.headers["content-disposition"]
    
    # Verify ZIP content is not empty
    assert len(response.content) > 0
    
    # Verify it's a valid ZIP file (starts with ZIP magic bytes)
    assert response.content[:4] == b'PK\x03\x04'


@pytest.mark.asyncio
async def test_generate_complaint_not_found(client):
    """Test POST /generate-complaint/{scan_id} with non-existent scan returns 404"""
    fake_id = uuid.uuid4()
    response = await client.post(f"/api/generate-complaint/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_complaint_bundle_contents(client, sample_scan):
    """Test that the generated ZIP bundle contains expected files"""
    import zipfile
    from io import BytesIO
    
    response = await client.post(f"/api/generate-complaint/{sample_scan.id}")
    assert response.status_code == 200
    
    # Read ZIP file
    zip_buffer = BytesIO(response.content)
    with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
        # Verify expected files exist
        file_list = zip_file.namelist()
        assert "scan_summary.json" in file_list
        assert "manifest.json" in file_list
        
        # Verify evidence files exist
        evidence_files = [f for f in file_list if f.startswith("evidence/")]
        assert len(evidence_files) == 2  # We created 2 snapshots
        
        # Verify scan_summary.json content
        summary_content = zip_file.read("scan_summary.json").decode()
        import json
        summary_data = json.loads(summary_content)
        
        assert "scan" in summary_data
        assert "listings" in summary_data
        assert summary_data["scan"]["id"] == str(sample_scan.id)
        assert len(summary_data["listings"]) == 2
        
        # Verify manifest.json content
        manifest_content = zip_file.read("manifest.json").decode()
        manifest_data = json.loads(manifest_content)
        
        assert "scan_summary.json" in manifest_data
        assert len(manifest_data) >= 3  # summary + 2 evidence files


# Made with Bob