import os
import tempfile
from pathlib import Path

from flask import Flask, jsonify, request, send_file
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.utils import secure_filename

from transformar_simple import transform_excel

BASE_DIR = Path(__file__).resolve().parent
ALLOWED_EXTENSIONS = {".xls", ".xlsx"}
TOKEN_MAX_AGE_SECONDS = int(os.getenv("TOKEN_MAX_AGE_SECONDS", str(60 * 60 * 8)))

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH_MB", "20")) * 1024 * 1024

secret_key = os.getenv("SECRET_KEY", "change-this-in-production")
app.config["SECRET_KEY"] = secret_key

cors_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()]
serializer = URLSafeTimedSerializer(secret_key, salt="dflex-auth-token")


def build_error(message: str, status_code: int = 400):
    return jsonify({"ok": False, "error": message}), status_code


def get_expected_username() -> str:
    return os.getenv("APP_USERNAME", "")


def get_expected_password() -> str:
    return os.getenv("APP_PASSWORD", "")


def generate_token(username: str) -> str:
    return serializer.dumps({"username": username})


def validate_token(token: str):
    try:
        data = serializer.loads(token, max_age=TOKEN_MAX_AGE_SECONDS)
        return data
    except SignatureExpired:
        raise ValueError("La sesión expiró. Volvé a iniciar sesión.")
    except BadSignature:
        raise ValueError("Token inválido.")


def require_auth():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise ValueError("Falta token de autorización.")
    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        raise ValueError("Token vacío.")
    return validate_token(token)


def get_force_d_file() -> Path | None:
    candidate = BASE_DIR / "forzar_D.txt"
    return candidate if candidate.exists() else None


@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin", "")
    if cors_origins and origin in cors_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        return ("", 204)


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "service": "dflex-transformador-api"})


@app.post("/api/login")
def login():
    expected_username = get_expected_username()
    expected_password = get_expected_password()

    if not expected_username or not expected_password:
        return build_error(
            "Faltan APP_USERNAME o APP_PASSWORD en las variables de entorno del backend.",
            500,
        )

    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""

    if username != expected_username or password != expected_password:
        return build_error("Usuario o contraseña incorrectos.", 401)

    token = generate_token(username)
    return jsonify({
        "ok": True,
        "token": token,
        "expires_in_seconds": TOKEN_MAX_AGE_SECONDS,
    })


@app.post("/api/transform")
def transform():
    try:
        require_auth()
    except ValueError as exc:
        return build_error(str(exc), 401)

    if "file" not in request.files:
        return build_error("No se recibió ningún archivo en el campo 'file'.")

    uploaded_file = request.files["file"]
    if not uploaded_file or not uploaded_file.filename:
        return build_error("El archivo está vacío o no tiene nombre.")

    original_name = secure_filename(uploaded_file.filename)
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        return build_error("Formato no soportado. Solo se aceptan archivos .xls o .xlsx.")

    with tempfile.TemporaryDirectory(prefix="dflex-transform-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        input_path = tmp_path / f"Lista base{suffix}"
        output_path = tmp_path / "Lista de import.xlsx"

        uploaded_file.save(input_path)

        try:
            transform_excel(input_path, output_path, force_d_file=get_force_d_file())
        except Exception as exc:
            return build_error(f"Error al transformar el archivo: {exc}", 400)

        return send_file(
            output_path,
            as_attachment=True,
            download_name="Lista de import.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
