"""GitHub Actions entry point for one bounded email-agent run."""

import importlib.util
import os
from pathlib import Path


class BatchLimitReached(RuntimeError):
    pass


class GeminiQuotaReached(RuntimeError):
    pass


def is_quota_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "429" in message
        or "resource_exhausted" in message
        or "quota exceeded" in message
    )


def load_agent():
    script = Path(__file__).with_name("metaknews@gmail.com.py")
    spec = importlib.util.spec_from_file_location("metaknews_agent", script)

    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load agent from {script}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def main() -> int:
    required = (
        "GMAIL_USER",
        "GMAIL_APP_PASSWORD",
        "GEMINI_API_KEY",
    )

    missing = [name for name in required if not os.getenv(name)]

    if missing:
        raise RuntimeError(
            "Missing required GitHub Actions secret(s): "
            + ", ".join(missing)
        )

    max_messages = max(
        1,
        int(os.getenv("MAX_MESSAGES_PER_RUN", "2"))
    )

    agent = load_agent()

    original_generate = agent.generate_gemini_response
    calls = 0

    def bounded_generate(prompt, *args, **kwargs):
        nonlocal calls

        if calls >= max_messages:
            raise BatchLimitReached(
                f"Per-run Gemini generation limit reached ({max_messages})."
            )

        try:
            result = original_generate(prompt, *args, **kwargs)

        except Exception as exc:
            if is_quota_error(exc):
                raise GeminiQuotaReached(str(exc)) from exc
            raise

        calls += 1
        return result

    agent.generate_gemini_response = bounded_generate

    try:
        agent.process_inbox()

    except BatchLimitReached as exc:
        print(
            f"[SAFE STOP] {exc} "
            "Remaining unread mail will be handled next run."
        )
        return 0

    except GeminiQuotaReached:
        print(
            "[SAFE STOP] Gemini quota exhausted. "
            "Ending batch without failing GitHub Actions."
        )
        return 0

    print(
        f"Run complete: {calls} Gemini draft generation(s)."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
