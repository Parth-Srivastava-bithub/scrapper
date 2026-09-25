import json
import os
import shutil
import subprocess


def sync_runpod_datacenters_cli():
    """Execute runpodctl to list datacenters in JSON format."""
    # Find runpodctl executable path (check PATH or default Windows path)
    runpodctl_path = shutil.which("runpodctl") or r"C:\Users\user\runpodctl.exe"

    if not os.path.exists(runpodctl_path) and not shutil.which("runpodctl"):
        raise FileNotFoundError(f"runpodctl executable not found at {runpodctl_path}")

    result = subprocess.run(
        [
            runpodctl_path,
            "datacenter",
            "list",
            "-o",
            "json",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)
