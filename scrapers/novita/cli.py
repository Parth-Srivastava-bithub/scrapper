import os
import shutil
import subprocess


class NovitaCLI:
    """Novita CLI wrapper for scraper tasks if needed."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("NOVITA_API_KEY")

    def run_cmd(self, args: list[str]) -> subprocess.CompletedProcess:
        novita_bin = shutil.which("novita") or "novita"
        cmd = [novita_bin]
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
