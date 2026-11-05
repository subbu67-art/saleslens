import os
from functools import wraps
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from werkzeug.utils import secure_filename
from analysis import load_sales, build_report, filter_sales, insights

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("SALES_DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_CSV = BASE_DIR / "data" / "sales.csv"
UPLOAD_CSV = DATA_DIR / "uploaded_sales.csv"
ALLOWED_EXTENSIONS = {"csv"}

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "change-this-before-deploying")
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

def admin_password():
    return os.environ.get("ADMIN_PASSWORD", "")

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Please sign in as an administrator to access this page.", "warning")
            return redirect(url_for("admin_login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper

def active_csv():
    return UPLOAD_CSV if UPLOAD_CSV.exists() else SAMPLE_CSV

def get_data():
    return load_sales(active_csv())

def filters_from_request():
    return {
        "start": request.args.get("start", "").strip(),
        "end": request.args.get("end", "").strip(),
        "region": request.args.get("region", "").strip(),
        "category": request.args.get("category", "").strip(),
    }

@app.context_processor
def inject_globals():
    return {"is_admin": bool(session.get("is_admin")), "data_source": "Uploaded dataset" if UPLOAD_CSV.exists() else "Sample dataset"}

@app.route("/")
def dashboard():
    df = filter_sales(get_data(), filters_from_request())
    report = build_report(df)
    return render_template("dashboard.html", report=report, filters=filters_from_request(),
                           regions=sorted(get_data()["region"].dropna().unique().tolist()),
                           categories=sorted(get_data()["category"].dropna().unique().tolist()))

@app.route("/insights")
def insights_page():
    df = filter_sales(get_data(), filters_from_request())
    return render_template("insights.html", stats=insights(df), report=build_report(df),
                           filters=filters_from_request())

@app.route("/sales")
def sales_page():
    df = filter_sales(get_data(), filters_from_request()).sort_values("date", ascending=False)
    q = request.args.get("q", "").strip().lower()
    if q:
        mask = df.astype(str).apply(lambda col: col.str.lower().str.contains(q, na=False)).any(axis=1)
        df = df[mask]
    rows = df.assign(date=df["date"].dt.strftime("%Y-%m-%d"),
                     revenue=df["revenue"].round(2)).to_dict("records")
    return render_template("sales.html", rows=rows, q=q, filters=filters_from_request())

@app.route("/upload", methods=["GET", "POST"])
@admin_required
def upload():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename:
            flash("Choose a CSV file first.", "error")
            return redirect(url_for("upload"))
        if Path(secure_filename(file.filename)).suffix.lower() not in ALLOWED_EXTENSIONS:
            flash("Only .csv files are accepted. Do not rename an Excel file to .csv.", "error")
            return redirect(url_for("upload"))
        try:
            df = load_sales(file)
            # Save only validated, normalized data. Atomic replace prevents partial files.
            temp = UPLOAD_CSV.with_suffix(".tmp")
            df.drop(columns=["revenue"]).to_csv(temp, index=False)
            temp.replace(UPLOAD_CSV)
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("upload"))
        flash(f"Upload successful: {len(df):,} valid sales rows are now active.", "success")
        return redirect(url_for("dashboard"))
    return render_template("upload.html")

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        configured = admin_password()
        if not configured:
            flash("Admin access is not configured. Set ADMIN_PASSWORD in Render environment variables.", "error")
        elif request.form.get("password", "") == configured:
            session["is_admin"] = True
            flash("Administrator session started.", "success")
            return redirect(request.args.get("next") or url_for("upload"))
        else:
            flash("Incorrect password.", "error")
    return render_template("login.html")

@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("dashboard"))

@app.route("/reset", methods=["POST"])
@admin_required
def reset():
    if UPLOAD_CSV.exists():
        UPLOAD_CSV.unlink()
    flash("Sample dataset restored.", "success")
    return redirect(url_for("dashboard"))

@app.route("/export")
def export_csv():
    df = filter_sales(get_data(), filters_from_request())
    export_path = DATA_DIR / "saleslens_export.csv"
    df.drop(columns=["revenue"]).to_csv(export_path, index=False)
    return send_file(export_path, as_attachment=True, download_name="saleslens_filtered_sales.csv", mimetype="text/csv")

@app.route("/health")
def health():
    return {"status": "ok", "rows": int(len(get_data())), "source": "uploaded" if UPLOAD_CSV.exists() else "sample"}

@app.errorhandler(413)
def too_large(_error):
    flash("File is too large. Maximum upload size is 8 MB.", "error")
    return redirect(url_for("upload"))

@app.errorhandler(ValueError)
def data_error(error):
    flash(str(error), "error")
    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
