```md
# PDF Converter Service (LibreOffice + Docker)

A small HTTP microservice that converts Office documents to PDF using **LibreOffice headless** running inside a **Linux Docker container**.

This repo is intentionally simple and POC-friendly: build the image, run the container, POST a file, get a PDF back.

---

## What this solves

- Convert **DOC/DOCX/RTF/ODT/XLS/XLSX/PPT/PPTX → PDF**
- No Microsoft Office required
- No LibreOffice installed on the host
- Runs as a containerized service (portable across machines and Azure container platforms)

---

## Tech stack

- Python + Flask (HTTP API)
- Gunicorn (production-ish HTTP server)
- LibreOffice (headless conversion)
- Docker (Linux container)

---

## Repo layout

```

pdf-converter-service/
app.py
requirements.txt
Dockerfile

````

---

## Prerequisites

### Local (Windows)
- **Docker Desktop** installed and running
- Docker set to **Linux containers** (default on most installs)
- Recommended: WSL2 enabled (Docker Desktop typically configures this)

Verify Docker is healthy:

```powershell
docker info
````

You should see `Context: desktop-linux` and `OSType: linux`.

---

## Build

From the repo folder:

```powershell
docker build -t pdf-converter:local .
```

---

## Run

```powershell
docker run --rm -p 8080:8080 pdf-converter:local
```

Leave that terminal open while testing.

---

## API

### Health check

```powershell
curl.exe http://localhost:8080/health
```

Expected:

```json
{"status":"ok"}
```

### Convert a file

**Option A (recommended on Windows): use `curl.exe`**

> In PowerShell, `curl` is an alias for `Invoke-WebRequest`. Use `curl.exe` to get real curl flags like `-F`.

```powershell
curl.exe -X POST "http://localhost:8080/convert" `
  -F "file=@C:\temp\test.docx" `
  --output C:\temp\test.pdf
```

**Option B: PowerShell-native**

```powershell
Invoke-WebRequest `
  -Uri "http://localhost:8080/convert" `
  -Method Post `
  -Form @{ file = Get-Item "C:\temp\test.docx" } `
  -OutFile "C:\temp\test.pdf"
```

---

## Supported file types

`doc`, `docx`, `rtf`, `odt`, `xls`, `xlsx`, `ppt`, `pptx`

If you send something else, the service returns **415 Unsupported Media Type**.

---

## How it works

* The service saves the uploaded file to a temporary working directory.

* It calls LibreOffice headless:

  `soffice --headless ... --convert-to pdf --outdir <out> <input>`

* A per-request LibreOffice user profile directory is used to avoid common headless locking issues.

* The resulting PDF is returned as the response body.

---

## Known limitations / tradeoffs (POC notes)

* **Fidelity depends on fonts.** If your documents use corporate fonts not present in the container, Linux will substitute fonts and output may shift.
* **Large images / complex documents** can take longer. The service currently has a conversion timeout.
* LibreOffice conversion is generally stable, but it’s still an external process—plan for retries/timeouts in production.
* This POC returns the PDF directly; production systems often store input/output in Blob storage and return a job ID.

---

## Troubleshooting

### Docker says it can’t connect / Linux engine missing

* Make sure Docker Desktop is running
* Ensure you’re using **Linux containers**
* Re-run:

```powershell
docker info
```

### PowerShell says `-X` is not a parameter for curl

You used PowerShell’s alias. Use `curl.exe`:

```powershell
curl.exe -X POST ...
```

### `apt-get` / `pip` fails during build

Corporate proxy/cert rules can block package installs. Capture the last ~20 lines of the build output and adjust Docker Desktop proxy settings accordingly.

### Conversion fails or no PDF produced

Check container logs (the terminal running `docker run`). LibreOffice stderr/stdout is returned in the error response for easier debugging.

---

## (Optional) Build once, ship the image

Instead of rebuilding on every machine:

```powershell
docker save pdf-converter:local -o pdf-converter.tar
```

On another machine:

```powershell
docker load -i pdf-converter.tar
docker run --rm -p 8080:8080 pdf-converter:local
```

---

## Next steps (production-hardening ideas)

* Add request size limits (protect memory/disk)
* Add structured logging + correlation IDs
* Add auth (API key / mTLS) for internal networks
* Store inputs/outputs in Azure Blob
* Queue-based conversion with Azure Service Bus (retries + scale)
* Run on Azure Container Apps or AKS

---

## License

This repo contains example code intended for internal/POC use. LibreOffice is licensed under open-source licenses; ensure your organization is comfortable with open-source usage policies.

```
::contentReference[oaicite:0]{index=0}
```
