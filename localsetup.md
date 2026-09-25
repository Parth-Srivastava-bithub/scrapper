# Native Local Setup Guide (Without Docker)

This guide walks you through setting up and running the **GPU Aggregator Scraper Worker** directly on your local machine using Python, Playwright, and your local Google Chrome browser—with **no Docker required**.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Step-by-Step Installation](#2-step-by-step-installation)
   - [Step 1: Clone the Repository](#step-1-clone-the-repository)
   - [Step 2: Create & Activate Virtual Environment](#step-2-create--activate-virtual-environment)
   - [Step 3: Install Dependencies & Playwright](#step-3-install-dependencies--playwright)
   - [Step 4: Configure Environment Variables (.env)](#step-4-configure-environment-variables-env)
3. [Starting Chrome for Browser Automation (CDP)](#3-starting-chrome-for-browser-automation-cdp)
4. [Optional: Install `runpodctl` CLI](#4-optional-install-runpodctl-cli)
5. [Running the Application](#5-running-the-application)
   - [Option A: Start the Full Scheduler](#option-a-start-the-full-scheduler)
   - [Option B: Run a Single Provider Sync](#option-b-run-a-single-provider-sync)
6. [Running Tests & Linting](#6-running-tests--linting)
7. [Troubleshooting Common Local Issues](#7-troubleshooting-common-local-issues)

---

## 1. Prerequisites

Before starting, ensure your system has the following installed:

- **Python 3.12+**: Verify with `python --version` (or `python3 --version`).
- **Git**: Verify with `git --version`.
- **Google Chrome** or **Chromium**: Needed for the RunPod web catalog scraper.
- **MongoDB**: A free MongoDB Atlas cluster or a locally running MongoDB instance.

---

## 2. Step-by-Step Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/Parth-Srivastava-bithub/scrapper.git
cd scrapper
```

---

### Step 2: Create & Activate Virtual Environment

Create an isolated virtual environment to prevent dependency conflicts with your system Python.

#### Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> **Note**: If PowerShell shows an `Execution_Policies` script restriction error, run:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```

#### Windows (Command Prompt - CMD):
```cmd
python -m venv .venv
.\.venv\Scripts\activate.bat
```

#### Linux / macOS (Bash / Zsh):
```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

### Step 3: Install Dependencies & Playwright

Once the virtual environment is activated:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
```

---

### Step 4: Configure Environment Variables (.env)

Create a `.env` file by copying the example template:

#### Windows (PowerShell):
```powershell
Copy-Item .env.example .env
```

#### Linux / macOS:
```bash
cp .env.example .env
```

Open `.env` in your editor and configure your credentials:

```ini
# MongoDB Connection
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB_NAME=gpu_aggregator

# Provider API Keys
RUNPOD_API_KEY=your_runpod_api_key_here
NOVITA_API_KEY=your_novita_api_key_here
VASTAI_API_KEY=your_vastai_api_key_here

# Local Chrome Remote Debugging Settings
CHROME_CDP_URL=http://127.0.0.1:9222
CDP_PORT=9222
CHROME_HEADLESS=new
```

#### How to get API Keys:
- **RunPod**: [runpod.io/console/user/settings](https://www.runpod.io/console/user/settings) &rarr; API Keys.
- **Novita AI**: [novita.ai/settings/key-management](https://novita.ai/settings/key-management) &rarr; Add Key.
- **Vast.ai**: [cloud.vast.ai/account](https://cloud.vast.ai/account/) &rarr; API Key.

---

## 3. Starting Chrome for Browser Automation (CDP)

The scraper worker uses:
- **Direct HTTP/REST APIs** for Vast.ai (No Chrome needed).
- **Direct REST APIs** for Novita AI (No Chrome needed).
- **GraphQL APIs** for RunPod live pricing (No Chrome needed).
- **Headless Chrome via Chrome DevTools Protocol (CDP)** on port `9222` to scrape dynamic web elements from the RunPod deploy console.

Before running the scheduler, start Chrome with remote debugging enabled in a separate terminal:

### Windows (PowerShell):
```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
  --remote-debugging-port=9222 `
  --user-data-dir="$HOME\chrome-scraper-profile" `
  --headless=new
```

### Windows (CMD):
```cmd
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%USERPROFILE%\chrome-scraper-profile" --headless=new
```

### Linux:
```bash
google-chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/chrome-scraper-profile" \
  --headless=new &
```

### macOS:
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/chrome-scraper-profile" \
  --headless=new &
```

### Verify Chrome is Listening:
Run this quick check to confirm the port is responding:
```bash
curl http://127.0.0.1:9222/json/version
```
If configured properly, you will see a JSON response with the Chrome version and WebSocket URL.

> **Tip**: If you do not launch Chrome, the scheduler will still run! It will log a warning for RunPod web scraping, skip it gracefully, and continue syncing Vast.ai, Novita AI, and RunPod GraphQL.

---

## 4. Optional: Install `runpodctl` CLI

RunPod's datacenter synchronizer (`maintainers/runpod.py`) discovers datacenters using the official `runpodctl` CLI.

- **Windows**: Download the binary from [RunPod Releases](https://github.com/runpod/runpodctl/releases) and place `runpodctl.exe` into a folder included in your system `PATH`.
- **Linux**:
  ```bash
  curl -sSL -o /usr/local/bin/runpodctl https://github.com/runpod/runpodctl/releases/download/v2.9.0/runpodctl-linux-amd64
  chmod +x /usr/local/bin/runpodctl
  ```
- **macOS**:
  ```bash
  curl -sSL -o /usr/local/bin/runpodctl https://github.com/runpod/runpodctl/releases/download/v2.9.0/runpodctl-darwin-all
  chmod +x /usr/local/bin/runpodctl
  ```

*(If `runpodctl` is not installed, the datacenter sync step will simply be skipped without crashing the worker).*

---

## 5. Running the Application

### Option A: Start the Full Scheduler

Make sure your virtual environment is active:

```bash
python scheduler.py
```

#### What happens:
1. Connects to MongoDB and builds required indexes.
2. Performs an **initial sync** of catalogs and datacenters for all providers (RunPod, Novita, Vast).
3. Starts the background APScheduler with recurring intervals:
   - **Every 5 minutes**: Live pricing & GPU availability sync.
   - **Every 1 hour**: Full GPU catalog refresh.
   - **Every 4 hours**: Datacenter and facility refresh.

---

### Option B: Run a Single Provider Sync

You can test any provider's maintainer individually from Python:

#### Sync Vast.ai:
```bash
python -c "from maintainers.vast import VastMaintainer; m = VastMaintainer(); m.update_catalog(); m.live_sync(); m.sync_datacenters()"
```

#### Sync Novita AI:
```bash
python -c "from maintainers.novita import NovitaMaintainer; m = NovitaMaintainer(); m.update_catalog(); m.live_sync(); m.sync_datacenters()"
```

#### Sync RunPod:
```bash
python -c "from maintainers.runpod import RunpodMaintainer; m = RunpodMaintainer(); m.update_catalog(); m.live_sync()"
```

---

## 6. Running Tests & Linting

### Run All Tests:
```bash
pytest tests/ -v
```

### Run Linter & Formatter:
```bash
# Check code style and rules
ruff check .

# Automatically format code
ruff format .
```

---

## 7. Troubleshooting Common Local Issues

### 1. `Activate.ps1 cannot be loaded because running scripts is disabled`
- **Cause**: PowerShell's default execution policy prevents unsigned script execution.
- **Fix**: Open PowerShell and run:
  ```powershell
  Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
  ```

### 2. `Could not connect to CDP at http://127.0.0.1:9222`
- **Cause**: Chrome was not launched with `--remote-debugging-port=9222`, or another application is using port 9222.
- **Fix**:
  1. Check if port 9222 is open: `curl http://127.0.0.1:9222/json/version`.
  2. Launch Chrome using the command in [Section 3](#3-starting-chrome-for-browser-automation-cdp).
  3. If another process is using port 9222, change `CDP_PORT=9223` in `.env` and pass `--remote-debugging-port=9223` to Chrome.

### 3. `ServerSelectionTimeoutError: No replica set members found`
- **Cause**: MongoDB Atlas has IP restrictions and does not recognize your current public IP address.
- **Fix**:
  1. Go to [MongoDB Atlas](https://cloud.mongodb.com/).
  2. Navigate to **Security** &rarr; **Network Access**.
  3. Click **Add IP Address** and add your current IP address (or select *Allow Access from Anywhere* for testing).

### 4. `ModuleNotFoundError: No module named '...'`
- **Cause**: Dependencies were installed outside of the active virtual environment.
- **Fix**: Ensure your shell prompt shows `(.venv)` before running `pip install -r requirements.txt`.
