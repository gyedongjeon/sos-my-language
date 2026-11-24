"""One entry point for calling any LLM provider (via LiteLLM)."""

import os
import threading

from pydantic import BaseModel, ValidationError

from .db import get_connection

# LiteLLM downloads its model price list when it is loaded unless told to use the one it ships
# with. Prices are not used here, and the download only slows down every start.
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

# Set once LiteLLM is loaded. Loading it takes seconds, so the server starts without it and
# loads it in the background (see `load`); a request that needs it sooner waits for it.
loaded = threading.Event()


def load():
    """LiteLLM, loaded on first use."""
    import litellm

    # Skip request parameters a given provider does not support instead of failing.
    litellm.drop_params = True
    loaded.set()
    return litellm


SETUP_HINT = "Choose a model and enter its API key on the Settings page."

class LLMError(Exception):
    """Raised with a user-facing message when the model cannot produce a reply."""


def llm_config() -> tuple[str, str | None]:
    """The model ("<provider>/<model>") and API key to use.

    The model saved on the Settings page comes first, with its saved key. Otherwise LLM_MODEL
    from the environment is used and LiteLLM reads that provider's key from the environment
    too (returned here as None).
    """
    with get_connection() as conn:
        rows = conn.execute("SELECT key, value FROM settings WHERE key IN ('llm_model', 'llm_api_key')")
        saved = {row["key"]: row["value"] for row in rows}
    if saved.get("llm_model"):
        return saved["llm_model"], saved.get("llm_api_key")
    return os.environ.get("LLM_MODEL", "").strip(), None


def complete(system: str, user: str | list[dict], **params) -> str:
    """Send one system + user message and return the model's text reply.

    `user` is plain text, or a list of content parts when sending audio. Extra keyword
    arguments (e.g. response_format, timeout) are passed through to LiteLLM.
    """
    model, api_key = llm_config()
    if api_key:
        params = {"api_key": api_key, **params}
    if not model:
        raise LLMError(f"No model is configured. {SETUP_HINT}")

    litellm = load()
    try:
        response = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            **{
                # Providers return transient 429/503 under load; retry a couple of times.
                "num_retries": 2,
                # Fail fast instead of leaving the conversation waiting on a stalled request.
                "timeout": 30,
                **params,
            },
        )
    except litellm.AuthenticationError as e:
        raise LLMError(f"The API key for {model} is missing or invalid. {SETUP_HINT}") from e
    except litellm.RateLimitError as e:
        raise LLMError("The LLM provider's rate limit was reached. Try again shortly.") from e
    except litellm.APIConnectionError as e:
        raise LLMError(f"Could not reach the LLM provider for {model}: {e}") from e
    except litellm.BadRequestError as e:
        # Includes an unknown provider prefix or model name.
        raise LLMError(f"The LLM provider rejected the request for {model}: {e}") from e
    except Exception as e:
        # LiteLLM's provider errors do not share one base class, so this is the boundary
        # that turns any remaining failure into a message for the UI.
        raise LLMError(f"LLM request failed for {model}: {e}") from e

    text = (response.choices[0].message.content or "").strip()
    if not text:
        raise LLMError("The model returned an empty reply.")
    return text


def format_conversation(messages: list[tuple[str, str]]) -> str:
    """Render (speaker, text) messages as a transcript, one line per message."""
    return "\n".join(f"{speaker}: {text}" for speaker, text in messages)


def parse_json_reply[T: BaseModel](reply: str, model: type[T]) -> T:
    """Validate a model's JSON reply against a schema."""
    # Some providers wrap JSON in a Markdown code fence.
    reply = reply.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
    try:
        return model.model_validate_json(reply)
    except ValidationError as e:
        raise LLMError(f"The model returned a reply in an unexpected format: {e}") from e
