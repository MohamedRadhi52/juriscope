"""Appels HTTP aux fournisseurs de modèles de langage.

Chaque fonction renvoie le même dict : modèle exact, texte produit et jetons consommés.
"""

import json
import os
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"


def post_json(url: str, payload: dict, headers: dict, attempts: int = 8) -> dict:
    """POST JSON ; attend puis réessaie si l'API signale une limite de débit ou une panne."""
    headers = headers | {"User-Agent": "juriscope"}
    request = Request(url, data=json.dumps(payload).encode(), headers=headers)
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=120) as response:
                return json.load(response)
        except HTTPError as error:
            retryable = error.code == 429 or error.code >= 500
            if not retryable or attempt == attempts - 1:
                detail = error.read().decode(errors="replace")[:500]
                raise RuntimeError(f"{url} a répondu {error.code} : {detail}") from error
            time.sleep(2**attempt)


def anthropic_complete(prompt: str, model: str) -> dict:
    payload = {
        "model": model,
        "max_tokens": 1024,
        "temperature": 0.7,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "x-api-key": os.environ["ANTHROPIC_API_KEY"],
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    data = post_json(ANTHROPIC_URL, payload, headers)
    return {
        "model": data["model"],
        "output": data["content"][0]["text"],
        "usage": {
            "input_tokens": data["usage"]["input_tokens"],
            "output_tokens": data["usage"]["output_tokens"],
        },
    }


def mistral_complete(prompt: str, model: str) -> dict:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0.7,
    }
    headers = {
        "Authorization": f"Bearer {os.environ['MISTRAL_API_KEY']}",
        "Content-Type": "application/json",
    }
    data = post_json(MISTRAL_URL, payload, headers)
    return {
        "model": data["model"],
        "output": data["choices"][0]["message"]["content"],
        "usage": {
            "input_tokens": data["usage"]["prompt_tokens"],
            "output_tokens": data["usage"]["completion_tokens"],
        },
    }
