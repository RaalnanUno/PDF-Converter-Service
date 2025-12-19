# 🐳 Dockerfile Walkthrough (Beginner-Friendly, Block-by-Block)

This `Dockerfile` is a **recipe** that tells Docker how to build an image that contains:

* Python (to run your Flask app)
* LibreOffice (to do the conversion)
* Your app code
* A startup command (Gunicorn server on port 8080)

---

## 1️⃣ Base image — “Start with a small Linux + Python”

```dockerfile
FROM python:3.11-slim
```

### What this means

* `FROM` picks the **starting point** for your image.
* `python:3.11-slim` is a lightweight Linux image with Python 3.11 preinstalled.

Why this matters:

* You don’t have to install Python yourself.
* “slim” keeps the image smaller (still not tiny once LibreOffice gets added).

> 🧠 Mental model: Docker images stack like layers.
> This line chooses the bottom layer.

---

## 2️⃣ Install LibreOffice and fonts — “Add the converter runtime”

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-impress \
    fonts-dejavu \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*
```

### What this means

This runs commands **inside the image at build time**:

### `apt-get update`

* Updates the list of available packages (like refreshing an app store list).

### `apt-get install ...`

* Installs LibreOffice + the specific components you need:

  * `libreoffice` (core runtime)
  * `writer` (Word-like documents: DOC/DOCX/RTF/ODT)
  * `calc` (Excel-like documents: XLS/XLSX)
  * `impress` (PowerPoint-like documents: PPT/PPTX)

### Font packages:

* `fonts-dejavu` and `fonts-liberation` provide common fonts.
* This reduces “weird PDF formatting” caused by missing fonts.

### `--no-install-recommends`

* “Install only what I asked for, don’t pull extra optional stuff.”
* Helps keep the image smaller.

### Cleanup:

```dockerfile
rm -rf /var/lib/apt/lists/*
```

* Removes cached package lists to shrink the final image.
* Not required, but very common best practice.

> 🧠 Key idea: LibreOffice is why this image is big — but also why it works without installing anything on the host.

---

## 3️⃣ Choose a working folder inside the container

```dockerfile
WORKDIR /app
```

### What this means

* Sets the default folder inside the container to `/app`.
* Any future commands like `COPY`, `RUN`, etc. will happen relative to `/app`.

It’s like doing:

```bash
cd /app
```

and staying there.

---

## 4️⃣ Copy Python dependency list

```dockerfile
COPY requirements.txt .
```

### What this means

* Copies `requirements.txt` from your repo into the container at `/app/requirements.txt`.

Why it’s split out (instead of copying everything at once):

* Docker caches layers.
* If you **don’t change** `requirements.txt`, Docker can reuse the cached pip install step next build.
* Faster rebuilds.

> 🧠 This is a “Docker optimization pattern.”

---

## 5️⃣ Install Python dependencies

```dockerfile
RUN pip install --no-cache-dir -r requirements.txt
```

### What this means

* Installs Flask + Gunicorn (whatever you listed).
* Happens at **image build time**, not when the container runs.

`--no-cache-dir`:

* Prevents pip from keeping install caches, which reduces image size.

---

## 6️⃣ Copy your application code into the image

```dockerfile
COPY app.py .
```

### What this means

* Copies your `app.py` into `/app/app.py` inside the container.

At this point, the image contains:

* Python + libs
* LibreOffice
* Your code

---

## 7️⃣ Document which port the container uses

```dockerfile
EXPOSE 8080
```

### What this means

This does **not** open the port by itself.

It’s more like:

> “This container intends to listen on port 8080.”

It’s metadata that helps:

* humans reading the Dockerfile
* tooling
* some container platforms

You still need:

```powershell
docker run -p 8080:8080 ...
```

---

## 8️⃣ Startup command — “What runs when the container starts?”

```dockerfile
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8080", "app:app"]
```

### What this means

When you run the container, Docker will execute this command.

Breakdown:

* `gunicorn` → the web server
* `-w 2` → run **2 worker processes**

  * more than 1 lets you handle multiple requests better
  * (each worker is a separate process)
* `-b 0.0.0.0:8080` → bind to all network interfaces on port 8080

  * **important inside containers**
  * if you bind to `127.0.0.1`, it won’t be reachable from outside the container
* `app:app` → means:

  * `app.py` file (module) named `app`
  * Flask app object inside it named `app`

So it reads like:

> “Run Gunicorn, serve the Flask app inside app.py, listen on 8080.”

---

# ✅ Summary (What this Dockerfile builds)

This Dockerfile creates an image that can:

* accept HTTP requests
* receive Office files
* run LibreOffice headless to convert them
* return PDFs
* without installing anything on the host

---

# 🧠 Beginner “Truth Table”

**Build time vs Run time**

### Build time (happens in `docker build`)

* Install LibreOffice
* Install fonts
* Install Python packages
* Copy your app code

### Run time (happens in `docker run`)

* Start Gunicorn
* Wait for HTTP requests
* Convert files on demand
