# Bugs deliberados: SQL injection, XSS, path traversal
import sqlite3
from flask import Flask, request, render_template_string

app = Flask(__name__)


@app.route("/user/<int:user_id>")
def get_user(user_id):
    conn = sqlite3.connect("app.db")
    # SQL injection: user_id debería ser parámetro
    row = conn.execute(
        f"SELECT * FROM users WHERE id = {user_id}"
    ).fetchone()
    return {"user": row}


@app.route("/search")
def search():
    q = request.args.get("q", "")
    # XSS: contenido sin escapar
    return render_template_string(f"<h1>Results for {q}</h1>")


@app.route("/file")
def read_file():
    name = request.args.get("name", "")
    # Path traversal
    with open(name) as fh:
        return fh.read()