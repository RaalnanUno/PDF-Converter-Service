import os
import shutil
import subprocess
import tempfile
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

ALLOWED_EXTS = {".doc", ".docx", ".rtf", ".odt", ".xls", ".xlsx", ".ppt", ".pptx"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/convert")
def convert():
    if "file" not in request.files:
        return jsonify(error="Missing form field 'file'"), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify(error="Empty filename"), 400

    _, ext = os.path.splitext(f.filename.lower())
    if ext not in ALLOWED_EXTS:
        return jsonify(error=f"Unsupported file type: {ext}", supported=sorted(ALLOWED_EXTS)), 415

    with tempfile.TemporaryDirectory() as workdir:
        in_path = os.path.join(workdir, f"input{ext}")
        out_dir = os.path.join(workdir, "out")
        os.makedirs(out_dir, exist_ok=True)

        f.save(in_path)

        # Convert using LibreOffice headless
        # - Use a dedicated user profile per request to avoid profile locking issues.
        lo_profile = os.path.join(workdir, "lo-profile")
        os.makedirs(lo_profile, exist_ok=True)

        cmd = [
            "soffice",
            "--headless",
            "--nologo",
            "--nolockcheck",
            "--nodefault",
            "--norestore",
            f"-env:UserInstallation=file://{lo_profile}",
            "--convert-to", "pdf",
            "--outdir", out_dir,
            in_path,
        ]

        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            return jsonify(error="Conversion timed out"), 504

        if proc.returncode != 0:
            return jsonify(
                error="LibreOffice conversion failed",
                stdout=proc.stdout[-2000:],
                stderr=proc.stderr[-2000:]
            ), 500

        # LibreOffice outputs a PDF with the same base name
        pdf_files = [p for p in os.listdir(out_dir) if p.lower().endswith(".pdf")]
        if not pdf_files:
            return jsonify(
                error="No PDF produced",
                stdout=proc.stdout[-2000:],
                stderr=proc.stderr[-2000:]
            ), 500

        pdf_path = os.path.join(out_dir, pdf_files[0])

        # Stream back the PDF
        return send_file(
            pdf_path,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=os.path.splitext(f.filename)[0] + ".pdf"
        )
