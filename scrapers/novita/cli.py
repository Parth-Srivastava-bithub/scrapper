import json
import os
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()


def get_novita_bin_path() -> str:
    """Find novita CLI binary in PATH or active virtual environment."""
    found = shutil.which("novita") or shutil.which("novita.exe")
    if found and os.path.exists(found):
        return found

    venv_scripts = os.path.join(sys.prefix, "Scripts", "novita.exe")
    if os.path.exists(venv_scripts):
        return venv_scripts

    venv_bin = os.path.join(sys.prefix, "bin", "novita")
    if os.path.exists(venv_bin):
        return venv_bin

    local_venv = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", ".scraper_venv", "Scripts", "novita.exe")
    )
    if os.path.exists(local_venv):
        return local_venv

    return "novita"


class NovitaCLI:
    """Novita CLI wrapper for scraper tasks."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("NOVITA_API_KEY")
        self.bin_path = get_novita_bin_path()

    def run_cmd(self, args: List[str]) -> subprocess.CompletedProcess:
        cmd = [self.bin_path]
        if self.api_key:
            cmd.extend(["--api-key", self.api_key])
        cmd.extend(args)
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env={**os.environ, "NOVITA_API_KEY": self.api_key or ""},
            check=True,
        )

    def get_products_table(self, gpu_num: int = 1) -> str:
        """Run `novita gpu products --gpu-num <n>` and return formatted ASCII table."""
        res = self.run_cmd(["gpu", "products", "--gpu-num", str(gpu_num)])
        return res.stdout

    def get_products_json(self, gpu_num: int = 1) -> List[Dict[str, Any]]:
        """Run `novita --json-output gpu products --gpu-num <n>` and return parsed items."""
        cmd = [self.bin_path]
        if self.api_key:
            cmd.extend(["--api-key", self.api_key])
        cmd.extend(["--json-output", "gpu", "products", "--gpu-num", str(gpu_num)])
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env={**os.environ, "NOVITA_API_KEY": self.api_key or ""},
            check=True,
        )
        data = json.loads(res.stdout)
        return data.get("data", [])

    def get_clusters(self) -> str:
        """Run `novita gpu clusters` and return cluster list output."""
        res = self.run_cmd(["gpu", "clusters"])
        return res.stdout
