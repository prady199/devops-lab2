from app import app

def test_health():
    assert app.test_client().get("/health").status_code == 200

def test_patients_need_token():
    assert app.test_client().get("/patients").status_code == 401

def test_root_redirects_to_login():
    r = app.test_client().get("/")
    assert r.status_code == 302 and "/login" in r.headers["Location"]

def test_login_page_shows_form():
    r = app.test_client().get("/login")
    assert r.status_code == 200 and b"Sign in" in r.data

def test_bad_login_rejected():
    r = app.test_client().post("/login", data={"username": "doctor", "password": "wrong"})
    assert r.status_code == 401

def test_good_login_opens_dashboard():
    c = app.test_client()
    assert c.post("/login", data={"username": "doctor", "password": "demo123"}).status_code == 302
    assert b"Ward overview" in c.get("/").data
