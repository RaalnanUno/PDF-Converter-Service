# 📄 LibreOffice PDF Converter – Code Walkthrough (Beginner-Friendly)

This file defines a **small HTTP service** that:

* accepts an uploaded Office document
* converts it to PDF using LibreOffice
* sends the PDF back to the caller

Think of it as:
**“Upload file → convert → download PDF”**

---

## 1️⃣ Imports — “What tools do we need?”

```py
import os
import shutil
import subprocess
import tempfile
from flask import Flask, request, send_file, jsonify
```

### What this means

You’re importing tools from Python’s standard library and Flask.

| Import       | Why it’s needed                             |
| ------------ | ------------------------------------------- |
| `os`         | Work with file paths and directories        |
| `shutil`     | (Not used here — safe to remove later)      |
| `subprocess` | Run LibreOffice as an external program      |
| `tempfile`   | Create safe, auto-cleaned temporary folders |
| `Flask`      | Create the web application                  |
| `request`    | Access uploaded files from HTTP requests    |
| `send_file`  | Send the PDF back to the user               |
| `jsonify`    | Return clean JSON error messages            |

> 🧠 Key idea:
> LibreOffice is **not a Python library** — it’s a separate program, so we must run it using `subprocess`.

---

## 2️⃣ Create the Flask app

```py
app = Flask(__name__)
```

This creates the **web application**.

Think of `app` as:

> “The thing that listens for HTTP requests and decides what to do.”

---

## 3️⃣ Allowed file types (basic safety)

```py
ALLOWED_EXTS = {".doc", ".docx", ".rtf", ".odt", ".xls", ".xlsx", ".ppt", ".pptx"}
```

This is a **whitelist** of file extensions you allow.

Why this matters:

* Prevents random uploads (`.exe`, `.zip`, etc.)
* Makes error messages clearer
* Protects LibreOffice from unexpected input

---

## 4️⃣ Health endpoint — “Are you alive?”

```py
@app.get("/health")
def health():
    return {"status": "ok"}
```

### What this does

* Creates a `GET /health` endpoint
* Returns a simple JSON response

Used for:

* Docker health checks
* Load balancers
* “Is the service running?”

If this returns `"ok"`, your container is alive.

---

## 5️⃣ Convert endpoint — the main logic

```py
@app.post("/convert")
def convert():
```

This defines:

* an HTTP **POST** endpoint at `/convert`
* this is where the file upload happens

---

## 6️⃣ Validate the upload

### Ensure a file was actually sent

```py
if "file" not in request.files:
    return jsonify(error="Missing form field 'file'"), 400
```

If the client forgets to include the file:

* return **400 Bad Request**
* explain what went wrong

---

### Ensure the filename isn’t empty

```py
f = request.files["file"]
if not f.filename:
    return jsonify(error="Empty filename"), 400
```

This catches broken uploads like:

* empty form submissions
* malformed requests

---

### Validate the file extension

```py
_, ext = os.path.splitext(f.filename.lower())
if ext not in ALLOWED_EXTS:
    return jsonify(error=f"Unsupported file type: {ext}", supported=sorted(ALLOWED_EXTS)), 415
```

What’s happening:

* Extract the file extension
* Check it against `ALLOWED_EXTS`
* If invalid → return **415 Unsupported Media Type**

> 🧠 This is a *polite rejection*, not a crash.

---

## 7️⃣ Create a temporary working directory

```py
with tempfile.TemporaryDirectory() as workdir:
```

This is **hugely important**.

* Creates a unique temp folder
* Automatically deletes it when done
* Prevents files from piling up
* Avoids cross-request collisions

Everything from here on lives **inside this temporary workspace**.

---

## 8️⃣ Prepare input and output paths

```py
in_path = os.path.join(workdir, f"input{ext}")
out_dir = os.path.join(workdir, "out")
os.makedirs(out_dir, exist_ok=True)
```

You are setting up:

* a known input file path (`input.docx`)
* a known output folder (`out/`)

Why not use the original filename?

* Avoids weird characters
* Avoids path traversal risks
* Keeps the logic predictable

---

## 9️⃣ Save the uploaded file

```py
f.save(in_path)
```

This writes the uploaded document to disk so LibreOffice can read it.

LibreOffice **cannot** read from memory — it needs a real file.

---

## 🔟 LibreOffice profile isolation (VERY important)

```py
lo_profile = os.path.join(workdir, "lo-profile")
os.makedirs(lo_profile, exist_ok=True)
```

LibreOffice normally:

* uses a shared user profile
* which causes crashes and locks in server mode

This creates:

* a **fresh profile per request**
* zero cross-request conflicts

> 🧠 This one line prevents 90% of “LibreOffice headless is flaky” issues.

---

## 1️⃣1️⃣ Build the LibreOffice command

```py
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
```

This is equivalent to running:

```bash
soffice --headless --convert-to pdf input.docx
```

But with extra flags to:

* disable UI
* disable recovery dialogs
* isolate the user profile
* control output location

This list format is safer than a shell string.

---

## 1️⃣2️⃣ Run LibreOffice safely

```py
try:
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=120
    )
except subprocess.TimeoutExpired:
    return jsonify(error="Conversion timed out"), 504
```

What this does:

* Runs LibreOffice
* Captures output
* Enforces a **2-minute timeout**

If LibreOffice hangs:

* kill it
* return **504 Gateway Timeout**

---

## 1️⃣3️⃣ Handle conversion failure

```py
if proc.returncode != 0:
    return jsonify(
        error="LibreOffice conversion failed",
        stdout=proc.stdout[-2000:],
        stderr=proc.stderr[-2000:]
    ), 500
```

If LibreOffice crashes:

* return **500 Internal Server Error**
* include recent logs (truncated)

This is *debug-friendly* and production-safe.

---

## 1️⃣4️⃣ Locate the generated PDF

```py
pdf_files = [p for p in os.listdir(out_dir) if p.lower().endswith(".pdf")]
```

LibreOffice:

* keeps the original filename
* just changes the extension

So we scan the output folder for `.pdf`.

---

### If no PDF was created

```py
if not pdf_files:
    return jsonify(
        error="No PDF produced",
        stdout=proc.stdout[-2000:],
        stderr=proc.stderr[-2000:]
    ), 500
```

This handles rare edge cases where LibreOffice exits cleanly but produces nothing.

---

## 1️⃣5️⃣ Send the PDF back to the client

```py
pdf_path = os.path.join(out_dir, pdf_files[0])
```

Now we know where the PDF is.

---

```py
return send_file(
    pdf_path,
    mimetype="application/pdf",
    as_attachment=True,
    download_name=os.path.splitext(f.filename)[0] + ".pdf"
)
```

This:

* streams the PDF back over HTTP
* sets correct headers
* forces a download
* preserves the original filename

---

## 🧠 Big-picture summary

This service:

1. Accepts a file over HTTP
2. Validates input
3. Creates a safe, isolated workspace
4. Runs LibreOffice headless
5. Handles errors cleanly
6. Returns the PDF
7. Cleans up automatically
