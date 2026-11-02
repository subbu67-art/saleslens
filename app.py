import os

from flask import Flask, flash, redirect, render_template, request, url_for

from analysis import build_report, load_sales

app = Flask(__name__)
app.secret_key = "change-this-secret-key"  # needed for flash messages

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV = os.path.join(BASE_DIR, "data", "sales.csv")
UPLOAD_CSV = os.path.join(BASE_DIR, "data", "uploaded.csv")


def current_csv():
    """Use the uploaded file if there is one, otherwise the sample data."""
    return UPLOAD_CSV if os.path.exists(UPLOAD_CSV) else DEFAULT_CSV


@app.route("/")
def dashboard():
    try:
        df = load_sales(current_csv())
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("upload"))

    using_upload = current_csv() == UPLOAD_CSV
    return render_template("index.html", report=build_report(df), using_upload=using_upload)


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            flash("Choose a CSV file first.", "error")
            return redirect(url_for("upload"))
        if not file.filename.lower().endswith(".csv"):
            flash("Only .csv files are supported.", "error")
            return redirect(url_for("upload"))

        try:
            df = load_sales(file)  # validate before saving
        except ValueError as error:
            flash(str(error), "error")
            return redirect(url_for("upload"))

        df.drop(columns=["revenue"]).to_csv(UPLOAD_CSV, index=False)
        flash("File uploaded. The dashboard now shows your data.", "success")
        return redirect(url_for("dashboard"))

    return render_template("upload.html")


@app.route("/reset")
def reset():
    """Go back to the sample data."""
    if os.path.exists(UPLOAD_CSV):
        os.remove(UPLOAD_CSV)
    flash("Showing the sample data again.", "success")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True)
