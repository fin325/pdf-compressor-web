"""
Tests für PDF Compressor Web App
Qualitätsstufen: Niedrig=50, Mittel=30, Gut=25
Ausführen: pytest test_app.py -v
"""

import io
import pytest
from unittest.mock import patch, MagicMock
from app import app


# ------------------- FIXTURES -------------------

@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["DEBUG"] = False
    with app.test_client() as client:
        yield client


def make_minimal_pdf():
    import fitz
    doc = fitz.open()
    page = doc.new_page(width=200, height=200)
    page.insert_text((50, 100), "Test PDF")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


# ------------------- ROUTE TESTS -------------------

def test_index_returns_200(client):
    response = client.get("/")
    assert response.status_code == 200


def test_wakeup_returns_ok(client):
    response = client.get("/wakeup")
    assert response.status_code == 200
    assert response.data == b"OK"


# ------------------- COMPRESS TESTS -------------------

def test_compress_no_file_returns_400(client):
    response = client.post("/compress", data={})
    assert response.status_code == 400


def test_compress_empty_filename_returns_400(client):
    response = client.post("/compress", data={
        "pdf_file": (io.BytesIO(b""), ""),
        "quality": "30"
    }, content_type="multipart/form-data")
    assert response.status_code == 400


def test_compress_niedrig_quality_50(client):
    """Qualitätsstufe Niedrig (quality=50)"""
    pdf_data = make_minimal_pdf()
    response = client.post("/compress", data={
        "pdf_file": (pdf_data, "test.pdf"),
        "quality": "50"
    }, content_type="multipart/form-data")
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.data[:4] == b"%PDF"


def test_compress_mittel_quality_30(client):
    """Qualitätsstufe Mittel (quality=30, Standard)"""
    pdf_data = make_minimal_pdf()
    response = client.post("/compress", data={
        "pdf_file": (pdf_data, "test.pdf"),
        "quality": "30"
    }, content_type="multipart/form-data")
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.data[:4] == b"%PDF"


def test_compress_gut_quality_25(client):
    """Qualitätsstufe Gut (quality=25)"""
    pdf_data = make_minimal_pdf()
    response = client.post("/compress", data={
        "pdf_file": (pdf_data, "test.pdf"),
        "quality": "25"
    }, content_type="multipart/form-data")
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.data[:4] == b"%PDF"


def test_gut_smaller_than_niedrig(client):
    """Gut (25) должен давать меньший файл чем Niedrig (50)"""
    pdf_data_1 = make_minimal_pdf()
    pdf_data_2 = make_minimal_pdf()

    r_niedrig = client.post("/compress", data={
        "pdf_file": (pdf_data_1, "test.pdf"), "quality": "50"
    }, content_type="multipart/form-data")

    r_gut = client.post("/compress", data={
        "pdf_file": (pdf_data_2, "test.pdf"), "quality": "25"
    }, content_type="multipart/form-data")

    assert len(r_gut.data) < len(r_niedrig.data)


def test_compress_default_quality(client):
    """Kein quality-Parameter → Default 30"""
    pdf_data = make_minimal_pdf()
    response = client.post("/compress", data={
        "pdf_file": (pdf_data, "test.pdf")
    }, content_type="multipart/form-data")
    assert response.status_code == 200


# ------------------- FEEDBACK TESTS -------------------

@patch("app.get_db_connection")
def test_feedback_get_returns_json(mock_conn, client):
    with patch("app.get_feedback", return_value={"likes": 5, "dislikes": 2, "percent": 71}):
        response = client.get("/feedback")
    assert response.status_code == 200
    data = response.get_json()
    assert "likes" in data
    assert "dislikes" in data
    assert "percent" in data


@patch("app.add_feedback", return_value="new")
@patch("app.get_feedback", return_value={"likes": 1, "dislikes": 0, "percent": 100})
def test_feedback_post_like(mock_get, mock_add, client):
    response = client.post("/feedback", data={"action": "like"})
    assert response.status_code == 200
    assert "likes" in response.get_json()


@patch("app.add_feedback", return_value="removed")
@patch("app.get_feedback", return_value={"likes": 0, "dislikes": 1, "percent": 0})
def test_feedback_post_dislike(mock_get, mock_add, client):
    response = client.post("/feedback", data={"action": "dislike"})
    assert response.status_code == 200
    assert "dislikes" in response.get_json()
