"""
Optional Ollama LLM integration for OpsGraph.

Expected public interface:
    available() -> bool
    generate(prompt: str) -> str

Environment variables:
    OLLAMA_HOST       default: http://127.0.0.1:11434
    OLLAMA_MODEL      default: llama3.2:3b
    OLLAMA_TIMEOUT    default: 120 seconds
    OLLAMA_NUM_PREDICT default: 128
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OLLAMA_HOST = os.getenv(
    "OLLAMA_HOST",
    "http://127.0.0.1:11434",
).rstrip("/")

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "llama3.2:3b",
)

OLLAMA_TIMEOUT = int(
    os.getenv("OLLAMA_TIMEOUT", "120")
)

OLLAMA_NUM_PREDICT = int(
    os.getenv("OLLAMA_NUM_PREDICT", "128")
)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _opener() -> urllib.request.OpenerDirector:
    """
    Create an urllib opener that does not use system HTTP proxies.

    This is important for local Ollama communication because corporate/
    system proxy settings can interfere with requests to 127.0.0.1.
    """
    proxy_handler = urllib.request.ProxyHandler({})
    return urllib.request.build_opener(proxy_handler)


def _request(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: int | None = None,
) -> dict[str, Any]:
    """
    Make a JSON HTTP request to Ollama.
    """

    data = None

    headers = {
        "Accept": "application/json",
    }

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )

    opener = _opener()

    with opener.open(
        request,
        timeout=timeout or OLLAMA_TIMEOUT,
    ) as response:

        raw = response.read().decode("utf-8")

    return json.loads(raw)


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------

def available() -> bool:
    """
    Return True if the configured Ollama model is available locally.
    """

    try:
        result = _request(
            f"{OLLAMA_HOST}/api/tags",
            method="GET",
            timeout=10,
        )

        models = result.get("models", [])

        for model in models:
            name = model.get("name", "")

            if (
                name == OLLAMA_MODEL
                or name.split(":")[0] == OLLAMA_MODEL.split(":")[0]
            ):
                return True

        return False

    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        ConnectionError,
        json.JSONDecodeError,
        OSError,
    ):
        return False


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def generate(prompt: str) -> str:
    """
    Generate an answer using the configured Ollama model.

    The response is non-streaming because OpsGraph's evaluation pipeline
    expects one complete response.
    """

    if not isinstance(prompt, str):
        raise TypeError("prompt must be a string")

    prompt = prompt.strip()

    if not prompt:
        raise ValueError("prompt cannot be empty")

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,

        # Keep the local benchmark predictable and reasonably fast.
        "options": {
            "temperature": 0,
            "num_predict": OLLAMA_NUM_PREDICT,
        },

        # Keep the model loaded between requests when possible.
        "keep_alive": "5m",
    }

    try:
        result = _request(
            f"{OLLAMA_HOST}/api/generate",
            method="POST",
            payload=payload,
            timeout=OLLAMA_TIMEOUT,
        )

    except urllib.error.HTTPError as exc:
        body = ""

        try:
            body = exc.read().decode("utf-8")
        except Exception:
            pass

        raise RuntimeError(
            f"Ollama HTTP error {exc.code}: {body}"
        ) from exc

    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not connect to Ollama at {OLLAMA_HOST}: {exc}"
        ) from exc

    except TimeoutError as exc:
        raise RuntimeError(
            f"Ollama request timed out after "
            f"{OLLAMA_TIMEOUT} seconds"
        ) from exc

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Ollama returned invalid JSON"
        ) from exc

    answer = result.get("response")

    if answer is None:
        raise RuntimeError(
            f"Ollama response did not contain 'response': {result}"
        )

    return str(answer).strip()


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

def configuration() -> dict[str, Any]:
    """
    Return the active Ollama configuration.

    Useful for debugging without exposing the actual prompt.
    """

    return {
        "host": OLLAMA_HOST,
        "model": OLLAMA_MODEL,
        "timeout": OLLAMA_TIMEOUT,
        "num_predict": OLLAMA_NUM_PREDICT,
    }


if __name__ == "__main__":
    print("OpsGraph Ollama configuration:")
    print(json.dumps(configuration(), indent=2))

    print()
    print("Checking Ollama...")

    if available():
        print(f"Model available: {OLLAMA_MODEL}")

        print()
        print("Running test generation...")

        response = generate(
            "Explain GraphRAG in one short sentence."
        )

        print()
        print(response)

    else:
        print(
            f"Model '{OLLAMA_MODEL}' is not available "
            f"at {OLLAMA_HOST}"
        )