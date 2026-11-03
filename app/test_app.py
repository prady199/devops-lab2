from app import app

def test_health():
    assert app.test_client().get("/health").status_code == 200

def test_patients_need_token():
    assert app.test_client().get("/patients").status_code == 401
