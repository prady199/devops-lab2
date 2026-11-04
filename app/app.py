import hmac, logging, os, socket
from flask import Flask, jsonify, redirect, render_template_string, request, session

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

COLOR = os.getenv("APP_COLOR", "none")
VERSION = os.getenv("APP_VERSION", "dev")
API_TOKEN = os.getenv("API_TOKEN", "")
LOGIN_USER = os.getenv("LOGIN_USER", "doctor")
LOGIN_PASSWORD = os.getenv("LOGIN_PASSWORD", "")
DEMO_MODE = not LOGIN_PASSWORD  # demo password is used only when no secret is configured

logging.basicConfig(level=logging.INFO)
audit = logging.getLogger("audit")

THEMES = {"blue": "#2563eb", "green": "#16a34a"}
PATIENTS = [  # synthetic data only
    {"id": 1, "name": "Test Patient A", "ward": "Cardiology", "status": "Stable"},
    {"id": 2, "name": "Test Patient B", "ward": "Neurology", "status": "Observation"},
    {"id": 3, "name": "Test Patient C", "ward": "Paediatrics", "status": "Discharged"},
]

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ 'Dashboard' if user else 'Sign in' }} - HealthApp</title>
<style>
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,"Segoe UI",Roboto,sans-serif;background:#f1f5f9;color:#0f172a}
.auth{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:16px;
 background:linear-gradient(135deg,{{ accent }}33,#f1f5f9 60%)}
.card{width:100%;max-width:380px;background:#fff;border-radius:16px;padding:32px 28px;
 box-shadow:0 10px 30px rgba(15,23,42,.12);text-align:center}
.logo{width:56px;height:56px;border-radius:14px;background:{{ accent }};display:flex;
 align-items:center;justify-content:center;margin:0 auto 16px}
h1{font-size:22px;margin:0 0 4px}.sub{color:#64748b;margin:0 0 20px;font-size:14px}
form{text-align:left}label{display:block;font-size:13px;font-weight:600;margin:14px 0 6px}
input{width:100%;padding:11px 12px;border:1px solid #cbd5e1;border-radius:10px;font-size:15px}
input:focus{outline:2px solid {{ accent }}66;border-color:{{ accent }}}
button{width:100%;margin-top:22px;padding:12px;border:0;border-radius:10px;background:{{ accent }};
 color:#fff;font-size:15px;font-weight:600;cursor:pointer}
button:hover{filter:brightness(.92)}
.err{background:#fef2f2;color:#b91c1c;border:1px solid #fecaca;border-radius:10px;padding:10px;
 font-size:14px;margin-bottom:6px}
.hint{font-size:12.5px;color:#64748b;margin:18px 0 0}
.badge{display:inline-block;margin-top:18px;padding:4px 10px;border-radius:999px;font-size:12px;
 background:{{ accent }}22;color:#0f172a}
.top{display:flex;justify-content:space-between;align-items:center;padding:14px 24px;background:{{ accent }};color:#fff}
.top a{color:#fff}.brand{font-weight:700;font-size:18px}
.wrap{max-width:900px;margin:24px auto;padding:0 16px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin:12px 0 24px}
.stat{background:#fff;border-radius:12px;padding:16px;box-shadow:0 2px 8px rgba(15,23,42,.06)}
.stat b{display:block;font-size:26px;color:{{ accent }}}
table{width:100%;border-collapse:collapse;background:#fff;border-radius:12px;overflow:hidden;
 box-shadow:0 2px 8px rgba(15,23,42,.06)}
th,td{text-align:left;padding:12px 14px;border-bottom:1px solid #e2e8f0;font-size:14px}
th{background:#f8fafc;color:#475569}
</style></head>
{% if user %}
<body>
<header class="top"><div class="brand">&#10010; HealthApp</div>
 <div>Signed in as <b>{{ user }}</b> &middot; <a href="/logout">Sign out</a></div></header>
<main class="wrap">
 <h2>Ward overview</h2>
 <div class="stats">
  <div class="stat"><b>{{ patients|length }}</b>Patients</div>
  <div class="stat"><b>2</b>Active wards</div>
  <div class="stat"><b>{{ version }}</b>App version</div>
 </div>
 <table><tr><th>ID</th><th>Name</th><th>Ward</th><th>Status</th></tr>
 {% for p in patients %}<tr><td>{{ p.id }}</td><td>{{ p.name }}</td><td>{{ p.ward }}</td><td>{{ p.status }}</td></tr>{% endfor %}
 </table>
 <span class="badge">{{ color|upper }} &middot; {{ version }} &middot; pod {{ host }}</span>
</main></body>
{% else %}
<body class="auth"><main class="card">
 <div class="logo"><svg viewBox="0 0 24 24" width="30" height="30" fill="#fff"><path d="M10 3h4v7h7v4h-7v7h-4v-7H3v-4h7z"/></svg></div>
 <h1>HealthApp Patient Portal</h1><p class="sub">Sign in to continue - v2</p>
 {% if error %}<div class="err">{{ error }}</div>{% endif %}
 <form method="post" action="/login">
  <label for="u">Username</label>
  <input id="u" name="username" autocomplete="username" required autofocus>
  <label for="p">Password</label>
  <input id="p" name="password" type="password" autocomplete="current-password" required>
  <button type="submit">Sign in</button>
 </form>
 {% if demo %}<p class="hint">Demo mode: user <b>doctor</b>, password <b>demo123</b></p>{% endif %}
 <span class="badge">{{ color|upper }} &middot; {{ version }} &middot; pod {{ host }}</span>
</main></body>
{% endif %}
</html>"""


def render(user=None, error=None, status=200):
    html = render_template_string(
        PAGE, user=user, error=error, demo=DEMO_MODE, patients=PATIENTS,
        accent=THEMES.get(COLOR, "#0d9488"), color=COLOR, version=VERSION,
        host=socket.gethostname())
    return html, status


def login_ok(username, password):
    expected = LOGIN_PASSWORD or "demo123"
    good_user = hmac.compare_digest(username.encode(), LOGIN_USER.encode())
    good_pass = hmac.compare_digest(password.encode(), expected.encode())
    return good_user and good_pass


@app.get("/")
def home():
    if not session.get("user"):
        return redirect("/login")
    return render(user=session["user"])


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        if login_ok(username, request.form.get("password", "")):
            session["user"] = username
            audit.info("LOGIN ok user=%r", username)
            return redirect("/")
        audit.warning("LOGIN failed user=%r", username)
        return render(error="Invalid username or password", status=401)
    return render()


@app.get("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.get("/health")
def health():
    return jsonify(status="ok", color=COLOR, version=VERSION)


def authorised():
    h = request.headers.get("Authorization", "")
    if not API_TOKEN or not h.startswith("Bearer "):
        return False
    return hmac.compare_digest(h[7:].encode(), API_TOKEN.encode())


@app.get("/patients")
def patients():
    if not authorised():
        audit.warning("DENIED path=%r", request.path)
        return jsonify(error="unauthorised"), 401
    audit.info("READ path=%r", request.path)
    return jsonify(PATIENTS)
