# How the Scraper Worker Works

This document explains the architecture of the containerized scraper, how the browser automation runs autonomously inside Docker, and answers common questions regarding Chrome and session management.

---

## 1. High-Level Architecture

```text
+-----------------------------------------------------------------------------------+
|                            Docker Container (gpu_scraper_worker)                  |
|                                                                                   |
|  +---------------------------+                +--------------------------------+  |
|  |   Headless Chromium       |  CDP (9222)    |       Scraper Application      |  |
|  |   (Running in background) | <------------> |       (Playwright + Python)    |  |
|  +-------------+-------------+  Internal Net  +---------------+----------------+  |
|                |                                              |                   |
|                v                                              v                   |
|  +---------------------------+                +--------------------------------+  |
|  |  Persistent Volume        |                |       MongoDB (External)       |  |
|  |  (/data/chrome-profile)   |                |  (gpu_catalog / datacenters)   |  |
|  +---------------------------+                +--------------------------------+  |
+-----------------------------------------------------------------------------------+
```

---

## 2. Step-by-Step Lifecycle

### Step 1: Container Startup & Lock Cleanup
When you run `docker compose up -d`:
1. `entrypoint.sh` executes as PID 1 inside the container.
2. It inspects `/data/chrome-profile` (the mounted volume) and removes any stale `SingletonLock` or `SingletonSocket` files. This ensures Chrome will never refuse to start if the container crashed or was killed abruptly previously.

### Step 2: Automated Chromium & CDP Launch
1. `entrypoint.sh` automatically launches the internal Chromium binary with:
   - `--headless=new`: Modern Chrome headless mode (runs full rendering, DOM, and JavaScript engines).
   - `--remote-debugging-port=9222`: Enables Chrome DevTools Protocol (CDP).
   - `--remote-debugging-address=127.0.0.1`: Keeps CDP bound strictly to local loopback (secure and unexposed).
   - `--user-data-dir=/data/chrome-profile`: Loads cookies, local storage, and session tokens from the persistent volume.
   - `--disable-dev-shm-usage` & `--no-sandbox`: Ensures stable execution inside containerized Linux.

### Step 3: CDP Health Check
Before launching the Python scheduler, `entrypoint.sh` polls `http://127.0.0.1:9222/json/version`.
- It retries every second until Chrome confirms it is ready to receive commands.
- If Chrome fails to start, it logs the error output and exits cleanly.

### Step 4: Python Scheduler Starts
Once CDP is healthy, `scheduler.py` is invoked:
1. **Schema Initialization**: Ensures MongoDB unique indexes on `gpu_id` and composite indexes on prices and availability.
2. **Initial Sync**:
   - **RunPod**: Connects Playwright over CDP to `127.0.0.1:9222`, navigates to `https://console.runpod.io/deploy`, scrapes available GPU hardware and prices, merges with GraphQL data, and upserts to MongoDB.
   - **Novita**: Queries the Novita API for catalog and regions, parsing GPU pricing, VRAM, and availability.
   - **Datacenters**: Runs `runpodctl` to sync 40+ RunPod datacenters and Novita regional locations.
3. **Continuous Scheduling (APScheduler)**:
   - Live updates every 5 minutes.
   - Catalog refreshes every 1 hour.
   - Datacenter syncs every 4 hours.

---

## 3. Why You Don't Have to Open Chrome Anymore

### Before (Local Development):
- You had to manually find the Chrome executable on Windows.
- You had to run a PowerShell command with `--remote-debugging-port=9222 --user-data-dir=...`.
- You had to keep a Chrome browser window open on your screen/taskbar.
- If you closed Chrome, the Python scrapers would fail with connection errors.

### Now (Containerized):
- **Chromium runs entirely inside Docker**: The container has its own Chromium binary and rendering engine.
- **Automatic Lifecycle Management**: Docker starts Chromium, sets up the CDP port, monitors health, and terminates it gracefully on `docker compose down`.
- **Headless Execution**: Chromium runs in the background without opening any desktop windows or interrupting your work.
- **Dynamic Page Navigation**: Playwright automatically opens and navigates tabs in the headless browser over CDP when scraping is needed.

---

## 4. Do You Ever Need to Open Chrome?

### The Short Answer:
**No for normal operation.** The container runs autonomously in the background.

---

### The Edge Case (One-Time Authentication / Cloudflare Captcha):
If a provider console requires a **manual login (2FA / CAPTCHA)** that cannot be automated:

1. **Option A: Pre-authenticate on Host (One-Time)**
   - Start local Chrome pointing to a folder (e.g. `C:\Users\user\chrome-profile`).
   - Log in manually to RunPod / Novita so your session cookies are saved.
   - Close local Chrome.
   - Bind-mount that folder into Docker:
     ```yaml
     volumes:
       - C:\Users\user\chrome-profile:/data/chrome-profile
     ```
   - From then on, Docker uses those saved cookies and you never have to open Chrome again.

2. **Option B: Use API Keys (Default)**
   - For APIs (RunPod GraphQL, Novita REST API), authentication is handled completely via `RUNPOD_API_KEY` and `NOVITA_API_KEY` in `.env`.
   - The Playwright scraper uses the headless browser to read live catalog DOM elements directly.

---

## 5. Summary Table

| Feature | Local (Old Way) | Docker Container (New Way) |
| :--- | :--- | :--- |
| **Chrome Process** | Manual start via Windows terminal | Automatic startup via `entrypoint.sh` |
| **Window Visibility** | Visible on desktop | Invisible (Headless Linux background) |
| **CDP Port (9222)** | Bound on Windows host | Internal loopback in container |
| **Session Cookies** | Local Windows profile | Docker volume (`/data/chrome-profile`) |
| **Cloud Deployment Ready** | No (tied to local machine) | Yes (can run on RunPod, Cloud Run, VPS) |
| **Graceful Shutdown** | Manual Ctrl+C on multiple windows | `docker compose down` |
