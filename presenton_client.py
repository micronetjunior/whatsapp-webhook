import os
import requests

class PresentonClient:
    def __init__(self):
        self.internal_url = os.getenv("PRESENTON_INTERNAL_URL")
        self.public_url = os.getenv("PRESENTON_PUBLIC_URL")

    def create_presentation(self, payload: dict):
        r = requests.post(
            f"{self.internal_url}/presentations",
            json=payload,
            timeout=60
        )
        r.raise_for_status()
        return r.json()

    def edit_url(self, edit_path: str):
        return f"{self.public_url}{edit_path}"

    def download_url(self, presentation_id: str):
        return f"{self.public_url}/presentations/{presentation_id}/download"
    