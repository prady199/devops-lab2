import hmac, logging, os, socket
from flask import Flask, jsonify, request

app = Flask(__name__)
COLOR = os.getenv("APP_COLOR", "none")
VERSION = os.getenv("APP_VERSION", "dev")
API_TOKEN = os.getenv("API_TOKEN", "")
logging.basicConfig(level=logging.INFO)
audit = logging.getLogger("audit")
BG = {"blue": "#1d4ed8", "green": "#15803d"}
PATIENTS = [  # synthetic data only
    {"id": 1, "name": "Test Patient A", "ward": "Cardiology"},
    {"id": 2, "name": "Test Patient B", "ward": "Neurology"},
]

@app.get("/")
def home():
    bg = BG.get(COLOR, "#374151")
    return (f'<body bgcolor="{bg}" text="white"><h1>HealthApp v2 {COLOR.upper()}</h1>'
            f'<h2>version {VERSION}</h2><p>pod {socket.gethostname()}</p></body>')

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
