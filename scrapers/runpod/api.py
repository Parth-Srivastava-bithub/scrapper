import os

from dotenv import load_dotenv

load_dotenv()


class RunpodScraperAPI:
    """RunPod REST API calls used for scraper data collection."""

    def __init__(self):
        self.api_key = os.getenv("RUNPOD_API_KEY")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        self.base_url = "https://rest.runpod.io/v1"
