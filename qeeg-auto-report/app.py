from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from flask import Flask, render_template, request, send_file, after_this_request
from werkzeug.utils import secure_filename

from qeeg_core import analyze_m00, build_report

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024

@app.get("/")
def index():
    return render_template("index.html")

@app.post("/analyze")
def analyze():
    uploaded = request.files.get("file")
    input_name = request.form.get("input_name", "").strip()
    if not uploaded or not uploaded.filename:
        return "m00ファイルを選択してください。", 400
    if not uploaded.filename.lower().endswith(".m00"):
        return "現在は.m00のみ対応しています。", 400

    td = TemporaryDirectory(prefix="qeeg_web_")
    work = Path(td.name)
    filename = secure_filename(uploaded.filename) or "input.m00"
    src = work / filename
    uploaded.save(src)

    try:
        result = analyze_m00(src)
        result.source_filename = Path(uploaded.filename).name
        out = work / (Path(uploaded.filename).stem + "_解析結果.docx")
        build_report(result, out, input_name=input_name)
    except Exception as e:
        td.cleanup()
        return f"解析エラー: {e}", 400

    @after_this_request
    def cleanup(response):
        response.call_on_close(td.cleanup)
        return response

    return send_file(
        out,
        as_attachment=True,
        download_name=out.name,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
