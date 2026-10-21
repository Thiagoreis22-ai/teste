"""Thiago Reis PRO: servidor privado para login, orçamentos e dados compartilhados.
Em produção, configure DATABASE_URL (PostgreSQL), SETUP_TOKEN e APP_ENV=production.
"""
import os, json, time, secrets, hashlib, hmac, sqlite3
from contextlib import contextmanager
from pathlib import Path
from flask import Flask, request, jsonify, make_response, g
from werkzeug.security import generate_password_hash, check_password_hash

BASE = Path(__file__).resolve().parent
PROD = os.getenv("APP_ENV") == "production"
DB_URL = os.getenv("DATABASE_URL", "")
SETUP_TOKEN = os.getenv("SETUP_TOKEN", "")
if PROD and (not DB_URL.startswith(("postgres://", "postgresql://")) or len(SETUP_TOKEN) < 24):
    raise RuntimeError("Configure DATABASE_URL PostgreSQL e SETUP_TOKEN seguro (24+ caracteres).")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024
app.json.ensure_ascii = False
if DB_URL.startswith(("postgres://", "postgresql://")):
    import psycopg
    from psycopg.rows import dict_row
    POSTGRES = True
else:
    POSTGRES = False
    DB_PATH = os.getenv("SQLITE_PATH", str(BASE / "thiago_dev.sqlite3"))

def connect():
    if POSTGRES:
        return psycopg.connect(DB_URL, row_factory=dict_row)
    db = sqlite3.connect(DB_PATH, timeout=15, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout = 15000")
    return db

def execute(db, statement, params=()):
    if POSTGRES:
        statement = statement.replace("?", "%s")
    return db.execute(statement, params)

@contextmanager
def transaction():
    db = connect()
    try:
        if not POSTGRES:
            db.execute("BEGIN IMMEDIATE")
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    with transaction() as db:
        execute(db, """CREATE TABLE IF NOT EXISTS users (
            role TEXT PRIMARY KEY, password_hash TEXT NOT NULL)""")
        execute(db, """CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY, role TEXT NOT NULL, expires_at BIGINT NOT NULL)""")
        execute(db, """CREATE TABLE IF NOT EXISTS app_state (
            id INTEGER PRIMARY KEY, revision INTEGER NOT NULL, payload TEXT NOT NULL)""")

init_db()

def bad(message, code=400):
    return jsonify(error=message), code

def auth():
    token = request.cookies.get("tr_sid", "")
    if not token:
        return None
    key = hashlib.sha256(token.encode()).hexdigest()
    with transaction() as db:
        row = execute(db, "SELECT s.role FROM sessions s JOIN users u ON u.role=s.role WHERE s.token_hash=? AND s.expires_at>?", (key, int(time.time()))).fetchone()
    return row["role"] if row else None

def issue_session(role):
    token = secrets.token_urlsafe(40)
    hashed = hashlib.sha256(token.encode()).hexdigest()
    with transaction() as db:
        execute(db, "DELETE FROM sessions WHERE expires_at<?", (int(time.time()),))
        execute(db, "INSERT INTO sessions(token_hash,role,expires_at) VALUES(?,?,?)", (hashed, role, int(time.time()) + 7 * 86400))
    resp = jsonify(ok=True, role=role)
    resp.set_cookie("tr_sid", token, max_age=7 * 86400, secure=PROD, httponly=True, samesite="Lax", path="/")
    return resp

def input_json():
    if not request.is_json:
        return None
    x = request.get_json(silent=True)
    return x if isinstance(x, dict) else None

@app.before_request
def guard():
    if request.path.startswith("/api/") and request.method != "GET":
        if not request.is_json:
            return bad("Requisição inválida.", 415)
        origin = request.headers.get("Origin")
        # Hospedagens como Cloud Run encerram o HTTPS antes do contêiner.
        expected_origin = ("https" if PROD else request.scheme) + "://" + request.host
        if origin and origin != expected_origin:
            return bad("Origem não autorizada.", 403)
        site = request.headers.get("Sec-Fetch-Site")
        if site and site not in ("same-origin", "none"):
            return bad("Requisição bloqueada.", 403)

@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Cache-Control"] = "no-store"
    if PROD:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

@app.get("/healthz")
def health():
    return jsonify(ok=True)

@app.get("/")
@app.get("/thiago-reis-pro/")
@app.get("/thiago-reis-pro/index.html")
def home():
    html = (BASE / "thiago-reis-pro" / "index.html").read_text(encoding="utf-8")
    html = html.replace("<head>", '<head><meta name="tr-cloud" content="connected">', 1)
    response = make_response(html)
    response.mimetype = "text/html"
    return response

@app.get("/api/status")
def status():
    with transaction() as db:
        configured = bool(execute(db, "SELECT 1 FROM users LIMIT 1").fetchone())
    return jsonify(configured=configured, role=auth())

@app.post("/api/setup")
def setup():
    data = input_json()
    if data is None or not SETUP_TOKEN or not hmac.compare_digest(str(data.get("setupCode", "")), SETUP_TOKEN):
        return bad("Código de configuração inválido.", 403)
    owner, employee = str(data.get("ownerPin", "")), str(data.get("employeePin", ""))
    if len(owner) < 8 or len(employee) < 8 or owner == employee or len(owner) > 128 or len(employee) > 128:
        return bad("Crie duas senhas diferentes de pelo menos 8 caracteres.")
    initial = data.get("initialData")
    if not isinstance(initial, dict) or not isinstance(initial.get("clients"), list):
        return bad("Dados iniciais inválidos.")
    with transaction() as db:
        if execute(db, "SELECT 1 FROM users LIMIT 1").fetchone():
            return bad("O sistema já foi configurado.", 409)
        execute(db, "INSERT INTO users(role,password_hash) VALUES(?,?)", ("dono", generate_password_hash(owner, method="scrypt")))
        execute(db, "INSERT INTO users(role,password_hash) VALUES(?,?)", ("funcionario", generate_password_hash(employee, method="scrypt")))
        execute(db, "INSERT INTO app_state(id,revision,payload) VALUES(1,1,?)", (json.dumps(initial, ensure_ascii=False),))
    return issue_session("dono")

LOGIN_FAILURES = {}
@app.post("/api/login")
def login():
    data = input_json() or {}
    role = str(data.get("role", ""))
    password = str(data.get("password", ""))
    if role not in ("dono", "funcionario") or len(password) > 128:
        return bad("Credenciais incorretas.", 401)
    # Limitador por usuário e IP (em memória, complemento às proteções do provedor).
    key = (request.remote_addr, role)
    now = time.monotonic()
    failures = [x for x in LOGIN_FAILURES.get(key, []) if now-x < 600]
    if len(failures) >= 8:
        return bad("Muitas tentativas. Tente mais tarde.", 429)
    with transaction() as db:
        row = execute(db, "SELECT password_hash FROM users WHERE role=?", (role,)).fetchone()
    if not row or not check_password_hash(row["password_hash"], password):
        failures.append(now)
        LOGIN_FAILURES[key] = failures
        return bad("Credenciais incorretas.", 401)
    LOGIN_FAILURES.pop(key, None)
    return issue_session(role)

@app.post("/api/logout")
def logout():
    token = request.cookies.get("tr_sid")
    if token:
        with transaction() as db:
            execute(db, "DELETE FROM sessions WHERE token_hash=?", (hashlib.sha256(token.encode()).hexdigest(),))
    resp = jsonify(ok=True)
    resp.delete_cookie("tr_sid", path="/")
    return resp

PROTECTED = ("quotes", "expenses", "incomes", "catalog", "settings")
EDITABLE_STAFF = ("clients", "jobs")
@app.get("/api/data")
def get_data():
    role = auth()
    if role is None:
        return bad("Entre novamente.", 401)
    with transaction() as db:
        row = execute(db, "SELECT revision,payload FROM app_state WHERE id=1").fetchone()
    if not row:
        return bad("Configuração pendente.", 503)
    doc = json.loads(row["payload"])
    if role == "funcionario":
        doc = {key: doc.get(key, []) for key in EDITABLE_STAFF}
    return jsonify(data=doc, revision=row["revision"], role=role)

@app.put("/api/data")
def put_data():
    role = auth()
    if role is None:
        return bad("Entre novamente.", 401)
    incoming = input_json()
    if not incoming or not isinstance(incoming.get("data"), dict) or type(incoming.get("revision")) is not int:
        return bad("Dados inválidos.")
    data = incoming["data"]
    with transaction() as db:
        query = "SELECT revision,payload FROM app_state WHERE id=1"
        if POSTGRES:
            query += " FOR UPDATE"
        row = execute(db, query).fetchone()
        if not row:
            return bad("Configuração pendente.", 503)
        if row["revision"] != incoming["revision"]:
            return bad("Outro aparelho alterou os dados. Recarregue.", 409)
        previous = json.loads(row["payload"])
        if role == "funcionario":
            # Nunca aceitar alterações nos campos financeiros/configurações do funcionário.
            for key in data:
                if key not in EDITABLE_STAFF and key not in ("version", *PROTECTED):
                    return bad("Campo não permitido.", 403)
            for key in EDITABLE_STAFF:
                if not isinstance(data.get(key), list):
                    return bad("Lista inválida.")
                previous[key] = data[key]
            updated = previous
        else:
            if any(not isinstance(data.get(k), list) for k in ("clients", "quotes", "jobs", "expenses", "incomes", "catalog")):
                return bad("Dados incompletos.")
            if not isinstance(data.get("settings"), dict):
                return bad("Configurações inválidas.")
            # Não persistir campos de senha da interface nos dados de negócio.
            data["settings"].pop("ownerPin", None)
            data["settings"].pop("employeePin", None)
            updated = data
        execute(db, "UPDATE app_state SET revision=?,payload=? WHERE id=1",
                (row["revision"]+1, json.dumps(updated, ensure_ascii=False),))
    return jsonify(revision=row["revision"]+1)

@app.put("/api/passwords")
def passwords():
    if auth() != "dono":
        return bad("Sem permissão.", 403)
    data = input_json() or {}
    current = str(data.get("currentPassword", ""))
    with transaction() as db:
        owner = execute(db, "SELECT password_hash FROM users WHERE role='dono'").fetchone()
        if not owner or not check_password_hash(owner["password_hash"], current):
            return bad("Senha atual incorreta.", 403)
        updates = {r: str(data.get(k, "")) for r,k in (("dono","ownerPin"), ("funcionario","employeePin"))}
        changed = [r for r,p in updates.items() if p]
        if not changed or any(len(updates[r]) < 8 or len(updates[r]) > 128 for r in changed):
            return bad("Senha nova precisa ter pelo menos 8 caracteres.")
        if updates["dono"] and updates["funcionario"] and updates["dono"] == updates["funcionario"]:
            return bad("As duas senhas devem ser diferentes.")
        for role in changed:
            execute(db, "UPDATE users SET password_hash=? WHERE role=?", (generate_password_hash(updates[role], method="scrypt"), role))
            execute(db, "DELETE FROM sessions WHERE role=?", (role,))
    return jsonify(ok=True, relogin=True)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "8000")), debug=False)
