import os
import sqlite3
import uuid
from datetime import UTC, datetime
from contextlib import contextmanager
from functools import wraps
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "instance" / "waste_management.db"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-only-change-this-secret")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)

DATABASE.parent.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_db():
    """Yield a SQLite connection and always close it after use."""
    conn = sqlite3.connect(str(DATABASE))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'citizen',
                created_at TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT NOT NULL UNIQUE,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                location TEXT NOT NULL,
                image_filename TEXT,
                status TEXT NOT NULL DEFAULT 'Submitted',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        admin_email = os.getenv("ADMIN_EMAIL", "admin@smartwaste.local")
        admin_password = os.getenv("ADMIN_PASSWORD", "Admin@123")
        exists = db.execute("SELECT id FROM users WHERE email = ?", (admin_email,)).fetchone()
        if not exists:
            db.execute(
                "INSERT INTO users (name,email,password_hash,role,created_at) VALUES (?,?,?,?,?)",
                ("System Admin", admin_email, generate_password_hash(admin_password), "admin", datetime.now(UTC).isoformat())
            )


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Admin access is required.", "danger")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.context_processor
def inject_user():
    return {"current_user": session.get("name"), "current_role": session.get("role")}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 8:
            flash("Enter your name, a valid email and a password of at least 8 characters.", "danger")
            return render_template("register.html")
        try:
            with get_db() as db:
                db.execute(
                    "INSERT INTO users (name,email,password_hash,role,created_at) VALUES (?,?,?,?,?)",
                    (name, email, generate_password_hash(password), "citizen", datetime.now(UTC).isoformat())
                )
            flash("Account created. Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("That email is already registered.", "danger")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with get_db() as db:
            user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session.update({"user_id": user["id"], "name": user["name"], "role": user["role"]})
            return redirect(url_for("admin_dashboard" if user["role"] == "admin" else "dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    with get_db() as db:
        complaints = db.execute(
            "SELECT * FROM complaints WHERE user_id = ? ORDER BY created_at DESC",
            (session["user_id"],)
        ).fetchall()
    return render_template("dashboard.html", complaints=complaints)


@app.route("/complaints/new", methods=["GET", "POST"])
@login_required
def new_complaint():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip()
        image = request.files.get("image")
        if not title or not description or not location:
            flash("Please complete all required fields.", "danger")
            return render_template("new_complaint.html")
        filename = None
        if image and image.filename:
            if not allowed_file(image.filename):
                flash("Upload a PNG, JPG, JPEG or WEBP image only.", "danger")
                return render_template("new_complaint.html")
            safe_name = secure_filename(image.filename)
            filename = f"{uuid.uuid4().hex}_{safe_name}"
            image.save(UPLOAD_DIR / filename)
        now = datetime.now(UTC).isoformat()
        ticket_id = "SWM-" + uuid.uuid4().hex[:8].upper()
        with get_db() as db:
            db.execute("""
                INSERT INTO complaints
                (ticket_id,user_id,title,description,location,image_filename,status,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (ticket_id, session["user_id"], title, description, location, filename, "Submitted", now, now))
        flash(f"Complaint submitted successfully. Your ticket ID is {ticket_id}.", "success")
        return redirect(url_for("dashboard"))
    return render_template("new_complaint.html")


@app.route("/admin")
@admin_required
def admin_dashboard():
    with get_db() as db:
        complaints = db.execute("""
            SELECT complaints.*, users.name AS user_name, users.email AS user_email
            FROM complaints JOIN users ON complaints.user_id = users.id
            ORDER BY complaints.created_at DESC
        """).fetchall()
        stats = {
            "total": db.execute("SELECT COUNT(*) FROM complaints").fetchone()[0],
            "submitted": db.execute("SELECT COUNT(*) FROM complaints WHERE status='Submitted'").fetchone()[0],
            "progress": db.execute("SELECT COUNT(*) FROM complaints WHERE status='In Progress'").fetchone()[0],
            "resolved": db.execute("SELECT COUNT(*) FROM complaints WHERE status='Resolved'").fetchone()[0],
        }
    return render_template("admin.html", complaints=complaints, stats=stats)


@app.route("/admin/complaints/<int:complaint_id>/status", methods=["POST"])
@admin_required
def update_status(complaint_id):
    status = request.form.get("status")
    if status not in {"Submitted", "In Progress", "Resolved"}:
        flash("Invalid status.", "danger")
        return redirect(url_for("admin_dashboard"))
    with get_db() as db:
        db.execute(
            "UPDATE complaints SET status=?, updated_at=? WHERE id=?",
            (status, datetime.now(UTC).isoformat(), complaint_id)
        )
    flash("Complaint status updated.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "service": "smart-waste-management"})


@app.route("/api/complaints")
@login_required
def api_complaints():
    with get_db() as db:
        rows = db.execute(
            "SELECT ticket_id,title,location,status,created_at FROM complaints WHERE user_id=? ORDER BY created_at DESC",
            (session["user_id"],)
        ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.errorhandler(413)
def too_large(_error):
    flash("Image is too large. Maximum upload size is 5 MB.", "danger")
    return redirect(url_for("new_complaint"))


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=os.getenv("FLASK_DEBUG", "0") == "1")
