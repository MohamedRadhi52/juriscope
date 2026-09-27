"""Appels HTTP aux fournisseurs de modèles de langage."""

import json
import os
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"


def post_json(url: str, payload: dict, headers: dict, attempts: int = 6) -> dict:
    """POST JSON ; attend puis réessaie si l'API signale une limite de débit ou une panne."""
    request = Request(url, data=json.dumps(payload).encode(), headers=headers)
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=120) as response:
                return json.load(response)
        except HTTPError as error:
            retryable = error.code == 429 or error.code >= 500
            if not retryable or attempt == attempts - 1:
                raise
            time.sleep(2**attempt)


def mistral_json(prompt: str, model: str, seed: int) -> dict:
    """Réponse d'un modèle Mistral en mode JSON, avec le modèle exact et l'usage en jetons."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0.7,
        "random_seed": seed,
    }
    headers = {
        "Authorization": f"Bearer {os.environ['MISTRAL_API_KEY']}",
        "Content-Type": "application/json",
    }
    data = post_json(MISTRAL_URL, payload, headers)
    return {
        "model": data["model"],
        "output": data["choices"][0]["message"]["content"],
        "usage": data["usage"],
    }
