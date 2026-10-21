"""Thiago Reis PRO: servidor privado para login, orçamentos e dados compartilhados.
Em produção, configure DATABASE_URL (PostgreSQL), SETUP_TOKEN e APP_ENV=production.
"""
import os, json, time, secrets, hashlib, hmac, sqlite3, base64, binascii
from contextlib import contextmanager
from pathlib import Path
from flask import Flask, request, jsonify, make_response, g, send_from_directory, abort
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
        execute(db, """CREATE TABLE IF NOT EXISTS job_photos (
            id TEXT PRIMARY KEY, job_id TEXT NOT NULL, kind TEXT NOT NULL,
            content TEXT NOT NULL, created_at TEXT NOT NULL, uploader TEXT NOT NULL)""")

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

@app.get("/<asset>")
def gold_assets(asset):
    if asset not in ("gold-theme.css", "responsive.css", "brand-gold.svg", "hero-gold.svg", "tr-icon.svg", "manifest.webmanifest", "sw.js", "apple-touch-icon.png", "icon-192.png", "icon-512.png"):
        abort(404)
    return send_from_directory(BASE / "thiago-reis-pro", asset, max_age=3600)

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

PROTECTED = ("quotes", "expenses", "incomes", "catalog", "settings", "stock", "stockMoves")
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
        private_fields = ("price", "labor", "rate", "payStatus", "quoteId", "stockApplied", "commission", "cost", "total")
        doc["jobs"] = [
            {key: value for key, value in job.items() if key not in private_fields}
            for job in doc.get("jobs", []) if isinstance(job, dict)
        ]
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
            old_jobs = {str(job.get("id")): job for job in previous.get("jobs", []) if isinstance(job, dict)}
            new_jobs = {str(job.get("id")): job for job in data["jobs"] if isinstance(job, dict)}
            if (len(new_jobs) != len(data["jobs"]) or not set(old_jobs).issubset(new_jobs)
                    or len(new_jobs) > 4000 or len(data["clients"]) > 4000):
                return bad("Ordens de serviço inválidas ou exclusão não permitida.", 403)
            allowed_fields = {"id", "clientId", "desc", "date", "time", "endTime",
                              "status", "notes", "assignedTo", "startedAt", "finishedAt",
                              "signature", "signedAt", "materials", "checklist"}
            merged_jobs = []
            for job_id, job in new_jobs.items():
                if not isinstance(job, dict) or len(job_id) > 100:
                    return bad("Ordem inválida.")
                original = old_jobs.get(job_id, {})
                entry = dict(original)
                entry.update({key: value for key, value in job.items() if key in allowed_fields})
                if not original:
                    entry.update({"price": 0, "labor": 0, "rate": 0, "payStatus": "pendente"})
                signature = entry.get("signature", "")
                if signature and (not isinstance(signature, str) or
                                  len(signature) > 180000 or
                                  not signature.startswith("data:image/png;base64,")):
                    return bad("Assinatura inválida.")
                merged_jobs.append(entry)
            previous["clients"] = data["clients"]
            previous["jobs"] = merged_jobs
            updated = previous
        else:
            if any(not isinstance(data.get(k), list) for k in ("clients", "quotes", "jobs", "expenses", "incomes", "catalog")):
                return bad("Dados incompletos.")
            if not isinstance(data.get("settings"), dict):
                return bad("Configurações inválidas.")
            # Não persistir campos de senha da interface nos dados de negócio.
            data["settings"].pop("ownerPin", None)
            data["settings"].pop("employeePin", None)
            data.setdefault("stock", previous.get("stock", []))
            data.setdefault("stockMoves", previous.get("stockMoves", []))
            if not isinstance(data["stock"], list) or not isinstance(data["stockMoves"], list):
                return bad("Estoque inválido.")
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

def job_exists(db, job_id):
    row = execute(db, "SELECT payload FROM app_state WHERE id=1").fetchone()
    if not row:
        return False
    try:
        return any(isinstance(job, dict) and str(job.get("id")) == job_id
                   for job in json.loads(row["payload"]).get("jobs", []))
    except (ValueError, TypeError):
        return False

@app.get("/api/job-photos/<job_id>")
def list_job_photos(job_id):
    if not auth():
        return bad("Entre novamente.", 401)
    if len(job_id) > 100:
        return bad("OS inválida.", 400)
    with transaction() as db:
        if not job_exists(db, job_id):
            return bad("OS não encontrada.", 404)
        rows = execute(db, "SELECT id,kind,created_at FROM job_photos WHERE job_id=? ORDER BY created_at", (job_id,)).fetchall()
    return jsonify(photos=[{"id": x["id"], "kind": x["kind"], "createdAt": x["created_at"]} for x in rows])

@app.post("/api/job-photos")
def add_job_photo():
    role = auth()
    if not role:
        return bad("Entre novamente.", 401)
    data = input_json() or {}
    job_id = str(data.get("jobId", ""))
    kind = str(data.get("kind", ""))
    encoded = data.get("data", "")
    prefix = "data:image/jpeg;base64,"
    if len(job_id) > 100 or len(job_id) < 4 or kind not in ("antes", "depois"):
        return bad("OS ou etapa inválida.")
    if not isinstance(encoded, str) or not encoded.startswith(prefix) or len(encoded) > 250000:
        return bad("Foto muito grande; compacte antes de enviar.")
    try:
        raw = base64.b64decode(encoded[len(prefix):], validate=True)
    except (binascii.Error, ValueError):
        return bad("Arquivo inválido.")
    if len(raw) < 50 or len(raw) > 180000 or not raw.startswith(b"\xff\xd8\xff"):
        return bad("Somente fotos JPEG compactadas são aceitas.")
    photo_id = secrets.token_hex(16)
    with transaction() as db:
        if not job_exists(db, job_id):
            return bad("Salve a ordem de serviço antes de anexar fotos.", 404)
        count = execute(db, "SELECT count(*) AS n FROM job_photos WHERE job_id=? AND kind=?", (job_id, kind)).fetchone()["n"]
        if count >= 4:
            return bad("Máximo de 4 fotos por etapa.", 409)
        execute(db, "INSERT INTO job_photos(id,job_id,kind,content,created_at,uploader) VALUES(?,?,?,?,?,?)",
                (photo_id, job_id, kind, encoded, time.strftime("%Y-%m-%d %H:%M:%S"), role))
    return jsonify(ok=True, id=photo_id)

@app.get("/api/job-photo/<photo_id>")
def view_job_photo(photo_id):
    if not auth():
        return bad("Entre novamente.", 401)
    if len(photo_id) != 32:
        return bad("Foto não encontrada.", 404)
    with transaction() as db:
        row = execute(db, "SELECT content FROM job_photos WHERE id=?", (photo_id,)).fetchone()
    if not row:
        return bad("Foto não encontrada.", 404)
    from flask import Response
    content = base64.b64decode(row["content"].split(",", 1)[1])
    response = Response(content, mimetype="image/jpeg")
    response.headers["Cache-Control"] = "private, no-store"
    return response

@app.delete("/api/job-photo/<photo_id>")
def remove_job_photo(photo_id):
    if auth() != "dono":
        return bad("Somente o proprietário pode excluir fotos.", 403)
    with transaction() as db:
        execute(db, "DELETE FROM job_photos WHERE id=?", (photo_id,))
    return jsonify(ok=True)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "8000")), debug=False)
