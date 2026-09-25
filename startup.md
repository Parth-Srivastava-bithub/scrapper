# Scraper Worker - Startup & Operation Guide

Welcome to the **GPU Aggregator Scraper Worker** repository. This service automatically scrapes, normalizes, and synchronizes real-time GPU compute availability, pricing, hardware specs, and datacenter locations from cloud providers (**RunPod**, **Novita AI**, and **Vast.ai**) into MongoDB.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [Environment Configuration](#3-environment-configuration)
4. [Startup Methods](#4-startup-methods)
   - [Method 1: Docker Compose (Recommended)](#method-1-docker-compose-recommended)
   - [Method 2: Standalone Docker Run](#method-2-standalone-docker-run)
   - [Method 3: Native Local Python Execution](#method-3-native-local-python-execution)
5. [Scheduler & Sync Cadence](#5-scheduler--sync-cadence)
6. [Testing & Code Quality](#6-testing--code-quality)
7. [Database Schema & Collections](#7-database-schema--collections)
8. [Troubleshooting & Common Issues](#8-troubleshooting--common-issues)
9. [Adding a New Provider](#9-adding-a-new-provider)

---

## 1. Architecture Overview

The worker combines direct provider REST / GraphQL APIs with containerized headless Chromium managed via the Chrome DevTools Protocol (CDP):

```
+----------------------------------------------------------------------------------+
|                            Docker Worker Container                               |
|                                                                                  |
|  +--------------------------+                +--------------------------------+  |
|  |   Headless Chromium      |  CDP (9222)    |       Python Application       |  |
|  |   (Managed entrypoint)   | <------------> |    - APScheduler               |  |
|  +------------+-------------+  Localhost     |    - Playwright CDP client     |  |
|               |                              |    - Requests (APIs)           |  |
|               v                              +---------------+----------------+  |
|  +--------------------------+                                |                   |
|  | Persistent Chrome Profile|                                v                   |
|  |   (/data/chrome-profile) |                +--------------------------------+  |
|  +--------------------------+                |       Target MongoDB Atlas     |  |
|                                              |  (`gpu_catalog`, `datacenters`)|  |
|                                              +--------------------------------+  |
+----------------------------------------------------------------------------------+
```

- **RunPod**: Uses GraphQL queries for catalog data and CDP-driven Playwright automation for live console prices/community cloud stock. Datacenter metadata is synced via the embedded `runpodctl` binary.
- **Novita AI**: Direct REST endpoints querying GPU catalog, specs, pricing tiers, and regional clusters.
- **Vast.ai**: REST endpoints fetching live bundles, machine hardware configurations, GPU fractional splits, and datacenter locations.
- **MongoDB**: Central document store with upserts, indexing on `gpu_id`, and TTL / heartbeat tracking.

---

## 2. Prerequisites

| Requirement | Docker Mode | Native Local Mode |
| :--- | :--- | :--- |
| **OS** | Windows, Linux, or macOS | Windows, Linux, or macOS |
| **Runtime** | Docker Engine 20.10+ & Docker Compose | Python 3.12+ & pip |
| **Browser** | Included in container (Chromium) | Google Chrome or Chromium installed |
| **Database** | MongoDB instance (Local or Atlas) | MongoDB instance (Local or Atlas) |
| **CLI Tool** | Included in container (`runpodctl`) | `runpodctl` (optional, for RunPod datacenters) |

---

## 3. Environment Configuration

Create a `.env` file in the root of the project:

```bash
cp .env.example .env
```

Populate the `.env` variables with your credentials:

```ini
# =========================================================
# MongoDB Connection
# =========================================================
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB_NAME=gpu_aggregator

# =========================================================
# Cloud Provider API Keys
# =========================================================
RUNPOD_API_KEY=your_runpod_api_key_here
NOVITA_API_KEY=your_novita_api_key_here
VASTAI_API_KEY=your_vastai_api_key_here

# =========================================================
# Chrome DevTools Protocol (CDP) Settings
# =========================================================
CDP_PORT=9222
CDP_HOST=127.0.0.1
CHROME_CDP_URL=http://127.0.0.1:9222
CHROME_HEADLESS=new
CHROME_USER_DATA_DIR=/data/chrome-profile
```

### Obtaining API Keys:
- **RunPod**: Sign in at [runpod.io/console/user/settings](https://www.runpod.io/console/user/settings) &rarr; *API Keys* &rarr; *Create API Key*.
- **Novita AI**: Sign in at [novita.ai/settings/key-management](https://novita.ai/settings/key-management) &rarr; *Add Key*.
- **Vast.ai**: Sign in at [cloud.vast.ai/account](https://cloud.vast.ai/account/) &rarr; Copy *API Key*.

> [!IMPORTANT]
> Never commit `.env` or files containing live credentials to Git. The `.gitignore` file is configured to exclude sensitive files.

---

## 4. Startup Methods

### Method 1: Docker Compose (Recommended)

Docker Compose builds and starts both Chromium and the Python scheduler inside an isolated Linux environment with all required system libraries and fonts.

#### Start in Background:
```bash
docker compose up -d --build
```

#### Follow Logs in Real Time:
```bash
docker compose logs -f scraper
```

#### Stop the Worker:
```bash
docker compose down
```

---

### Method 2: Standalone Docker Run

Run the container directly using the pre-built image without cloning the repository or using docker-compose.

#### On Windows (PowerShell):
```powershell
docker run -d `
  --name gpu-scraper-worker `
  --restart unless-stopped `
  -e MONGODB_URI="mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority" `
  -e MONGODB_DB_NAME="gpu_aggregator" `
  -e RUNPOD_API_KEY="your_runpod_api_key" `
  -e NOVITA_API_KEY="your_novita_api_key" `
  -e VASTAI_API_KEY="your_vastai_api_key" `
  -e CDP_PORT="9222" `
  -e CHROME_HEADLESS="new" `
  -e CHROME_USER_DATA_DIR="/data/chrome-profile" `
  -v scraper_chrome_profile:/data/chrome-profile `
  --shm-size=2g `
  yellowforest/gpu-scraper-worker:latest
```

#### On Linux / macOS (Bash):
```bash
docker run -d \
  --name gpu-scraper-worker \
  --restart unless-stopped \
  -e MONGODB_URI="mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority" \
  -e MONGODB_DB_NAME="gpu_aggregator" \
  -e RUNPOD_API_KEY="your_runpod_api_key" \
  -e NOVITA_API_KEY="your_novita_api_key" \
  -e VASTAI_API_KEY="your_vastai_api_key" \
  -e CDP_PORT="9222" \
  -e CHROME_HEADLESS="new" \
  -e CHROME_USER_DATA_DIR="/data/chrome-profile" \
  -v scraper_chrome_profile:/data/chrome-profile \
  --shm-size=2g \
  yellowforest/gpu-scraper-worker:latest
```

---

### Method 3: Native Local Python Execution

Run the worker directly on your host machine for development or debugging.

#### Step 3.1: Create and Activate Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv .scraper_venv
.\.scraper_venv\Scripts\Activate.ps1
```

**Linux / macOS (Bash):**
```bash
python3 -m venv .scraper_venv
source .scraper_venv/bin/activate
```

#### Step 3.2: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
```

#### Step 3.3: Launch Chrome with Remote Debugging (CDP)

The Playwright browser automation connects to Chrome over CDP port 9222. Start a dedicated Chrome instance before running the scheduler:

**Windows (PowerShell):**
```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
  --remote-debugging-port=9222 `
  --user-data-dir="$HOME\chrome-scraper-profile" `
  --headless=new
```

**Linux (Bash):**
```bash
google-chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/chrome-scraper-profile" \
  --headless=new &
```

**macOS (Bash):**
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/chrome-scraper-profile" \
  --headless=new &
```

#### Step 3.4: Verify CDP Connection
Open your browser or curl:
```bash
curl http://127.0.0.1:9222/json/version
```
You should receive a JSON response showing the browser version and WebSocket debugger URL.

#### Step 3.5: Run the Scheduler
```bash
python scheduler.py
```

---

## 5. Scheduler & Sync Cadence

When `scheduler.py` runs, it executes an **initial sync** across all providers, followed by recurring background jobs:

| Task | Target Providers | Cadence | Purpose |
| :--- | :--- | :--- | :--- |
| **Initial Sync** | RunPod, Novita, Vast | On startup | Full baseline database seeding |
| **Live Sync** | RunPod, Novita, Vast | Every **5 minutes** | Real-time prices, spot/secure tiers, active availability |
| **Catalog Update** | RunPod, Novita, Vast | Every **1 hour** | GPU models, VRAM specs, baseline pricing & architectures |
| **Datacenter Sync** | RunPod, Novita, Vast | Every **4 hours** | Geographic locations, datacenter codes, country info |

---

## 6. Testing & Code Quality

### Run Unit & Integration Tests:
```bash
pytest tests/ -v
```

### Run Linter & Style Checks:
```bash
ruff check .
```

### Format Code:
```bash
ruff format .
```

---

## 7. Database Schema & Collections

Data is written to two primary collections in the configured MongoDB database (`gpu_aggregator`):

### 1. `gpu_catalog`
Stores consolidated GPU models with pricing and availability:
- `gpu_id` (Unique index): Unique identifier (e.g. `runpod_A100-SXM4-80GB`, `novita_RTX-4090`, `vast_RTX_4090`)
- `provider`: Provider slug (`runpod`, `novita`, `vast`)
- `gpu_name`: Normalized GPU name
- `vram_gb`: Total VRAM in gigabytes
- `prices`: Hourly pricing options (`on_demand`, `spot`, `interruptible`, `community`)
- `availability`: Stock count, rentable status, or region availability
- `updated_at`: UTC timestamp of last successful sync

### 2. `datacenters`
Stores geographic facilities and datacenter codes:
- `provider`: Provider slug
- `datacenter_id`: Provider location ID (e.g., `US-NJ-1`, `us-west-1`)
- `name`: Human-readable name
- `country`: Two-letter ISO country code or full name
- `features`: Supported networking, security tiers, storage types

---

## 8. Troubleshooting & Common Issues

### Issue 1: `SingletonLock` or Chrome Fails to Start
- **Cause**: Chrome was killed abruptly while writing to the profile directory.
- **Fix**: The container `entrypoint.sh` automatically removes stale locks on startup. In local mode, remove the file manually:
  ```bash
  rm -f "$HOME/chrome-scraper-profile/SingletonLock"
  ```

### Issue 2: `Could not connect to CDP at http://127.0.0.1:9222`
- **Cause**: Chrome is not running with `--remote-debugging-port=9222` or another process is occupying port 9222.
- **Fix**: Verify with `curl http://127.0.0.1:9222/json/version` or change `CDP_PORT` in `.env`.

### Issue 3: `pymongo.errors.ServerSelectionTimeoutError`
- **Cause**: MongoDB Atlas IP Access List is blocking the worker IP, or `MONGODB_URI` credentials are invalid.
- **Fix**: In MongoDB Atlas, go to **Network Access** &rarr; **Add IP Address** &rarr; allow your current IP address (or `0.0.0.0/0` if using dynamic container IPs).

### Issue 4: Docker Memory Crashes (`shm-size`)
- **Cause**: Headless Chromium exhausts `/dev/shm` default size (64MB) during heavy page rendering.
- **Fix**: Always specify `--shm-size=2g` in `docker run` or `shm_size: "2gb"` in `docker-compose.yml` (already configured).

---

## 9. Adding a New Provider

To add support for a new cloud GPU provider (e.g., Lambda Labs, Hyperstack, Clore):

1. **Scraper**: Create `scrapers/<provider>/` containing API clients or Playwright scraping routines.
2. **Maintainer**: Subclass `BaseMaintainer` in `maintainers/<provider>.py` implementing:
   - `update_catalog()`
   - `sync_datacenters()`
   - `live_sync()`
3. **Register in Scheduler**: Import and instantiate the maintainer in `scheduler.py` and register the three corresponding jobs in `scheduler.add_job()`.
4. **Tests**: Add test coverage under `tests/test_scrapers.py` and `tests/test_maintainers.py`.
