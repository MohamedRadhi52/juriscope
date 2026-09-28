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
AZURE_API_VERSION = "2024-10-21"
# dollars par million de jetons, en entrée puis en sortie (tarifs publics, septembre 2026)
PRICES = {"claude-haiku-4-5-20251001": (1.0, 5.0), "claude-sonnet-5-5": (2.0, 10.0)}


def cost(usages: list[dict], model: str) -> float:
    """Coût en dollars d'une série d'appels."""
    price_in, price_out = PRICES[model]
    return sum(u["input_tokens"] * price_in + u["output_tokens"] * price_out for u in usages) / 1e6


def extract_json(text: str) -> dict | None:
    """Objet JSON d'une réponse, même entouré de texte ou d'un bloc de code."""
    start, end = text.find("{"), text.rfind("}")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


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
            # l'API indique parfois combien de secondes attendre avant de réessayer
            time.sleep(max(2**attempt, float(error.headers.get("retry-after") or 0)))


def anthropic_complete(prompt: str, model: str, temperature: float = 0.7) -> dict:
    payload = {
        "model": model,
        "max_tokens": 1024,
        "temperature": temperature,
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
        # le texte suit parfois un bloc de réflexion : on prend le premier bloc de texte
        "output": next(block["text"] for block in data["content"] if block["type"] == "text"),
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


def azure_openai_complete(prompt: str, model: str) -> dict:
    """Azure OpenAI : model est le nom du déploiement, créé dans la ressource Azure.

    Variables attendues : AZURE_OPENAI_ENDPOINT (https://<ressource>.openai.azure.com) et
    AZURE_OPENAI_API_KEY.
    """
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
    url = f"{endpoint}/openai/deployments/{model}/chat/completions?api-version={AZURE_API_VERSION}"
    payload = {"messages": [{"role": "user", "content": prompt}], "temperature": 0.7}
    headers = {"api-key": os.environ["AZURE_OPENAI_API_KEY"], "Content-Type": "application/json"}
    data = post_json(url, payload, headers)
    return {
        "model": data["model"],
        "output": data["choices"][0]["message"]["content"],
        "usage": {
            "input_tokens": data["usage"]["prompt_tokens"],
            "output_tokens": data["usage"]["completion_tokens"],
        },
    }
