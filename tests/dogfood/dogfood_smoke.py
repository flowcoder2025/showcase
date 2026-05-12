"""Phase 3-Pkg T46 — External consumer dogfood smoke.

Simulates a downstream project importing ``flowcoder-office-tools`` from a
fresh virtualenv. Validates:

1. Every public sub-module (per T45 ``__all__``) imports cleanly.
2. ``safe_backends()`` and a user-defined ``FakeBackend`` both satisfy the
   :class:`Backends` DI surface (R3-H1).
3. ``serialize_result`` / ``as_display`` mask synthetic secret sentinels
   (R1-C1 single sanitizer).
4. No production secret env is leaked into the dogfood process (R1-C2 +
   R2-H6) — see ``SECRET_ENV_NAMES`` below.

Run via ``env -i PATH=... python -m dogfood_smoke`` (see CI workflow).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

SECRET_ENV_NAMES = [
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
    "DISCORD_WEBHOOK_URL",
    "GMAIL_OAUTH_TOKEN",
    "GMAIL_OAUTH_CREDENTIALS",
    "GMAIL_TOKEN_PATH",
    "GMAIL_SENDER",
    "SMTP_HOST",
    "SMTP_USER",
    "SMTP_PASS",
    "AX_OCR_BASE_URL_E2B",
    "AX_OCR_BASE_URL_E4B",
    "AX_OCR_MODEL_E2B_PATH",
    "AX_OCR_MODEL_E4B_PATH",
]

_leaked = [k for k in SECRET_ENV_NAMES if os.environ.get(k)]
assert not _leaked, f"dogfood smoke detected leaked secret env: {_leaked}"


def main() -> int:
    # 1. Public sub-module surface (matches T45 __all__).
    from flowcoder_office_tools.ai import client, prompts, tasks
    from flowcoder_office_tools.backends import factory, safe
    from flowcoder_office_tools.common import (
        config,
        demo_logger,
        safe_mode,
        safe_mode_v2,
        secrets_mask,
        timer,
    )
    from flowcoder_office_tools.docgen import hwp_preview, hwpx, pdf, template, word
    from flowcoder_office_tools.excel import merger, pivot, reader, validator, writer
    from flowcoder_office_tools.messaging import discord as discord_mod
    from flowcoder_office_tools.messaging import email as email_mod
    from flowcoder_office_tools.ocr import gemma, invoice, receipt
    from flowcoder_office_tools.protocols import (
        Backends,
        ScenarioResult,
        as_display,
        serialize_result,
    )

    # Touch each sub-module so the import is not silently elided.
    assert callable(reader.read_dir)
    assert callable(merger.merge_by_vendor)
    assert callable(pivot.vendor_by_month)
    assert callable(writer.write_styled_report)
    assert callable(validator.detect_unit_price_outliers)
    assert callable(discord_mod.send_with_level)
    assert callable(email_mod.build_message)
    assert callable(hwp_preview.render_preview)
    assert callable(hwpx.fill_form)
    assert callable(pdf.md_to_pdf)
    assert callable(template.render_string)
    assert callable(word.build_quote)
    assert callable(gemma.extract)
    assert callable(invoice.extract)
    assert callable(receipt.extract)
    assert callable(client.chat)
    assert callable(prompts.email_draft_user)
    assert callable(tasks.draft_email)
    assert callable(config.repo_root)
    assert callable(demo_logger.demo_logger)
    assert callable(safe_mode.is_safe)
    assert callable(safe_mode_v2.is_safe)
    assert callable(secrets_mask.mask_text)
    assert callable(timer.measure)
    assert callable(factory.safe_backends)
    assert callable(safe.SafeOCRBackend)

    # 2. SafeBackend wiring (Backends accepts Protocol implementations).
    safe_backs = factory.safe_backends()
    assert isinstance(safe_backs, Backends)
    assert safe_backs.ocr is not None
    assert safe_backs.ai is not None
    assert safe_backs.msg is not None

    # 3. FakeBackend wiring — external project's own Protocol impl (R3-H1).
    from fake_backend import FakeOCRBackend, fake_backends

    fakes = fake_backends()
    assert isinstance(fakes, Backends)
    assert isinstance(fakes.ocr, FakeOCRBackend)
    initial_calls = fakes.ocr.calls
    fakes.ocr.extract(Path(__file__), model="gemma4:e2b", schema=None)
    assert fakes.ocr.calls == initial_calls + 1

    # 4. ScenarioResult shape (5+1 required fields).
    sample: ScenarioResult = {
        "case_id": "smoke",
        "summary_text": "ok",
        "output_files": [],
        "metrics": {},
        "failures": [],
        "extras": {},
    }
    assert set(sample.keys()) == {
        "case_id",
        "summary_text",
        "output_files",
        "metrics",
        "failures",
        "extras",
    }

    # 5. serialize_result + as_display mask synthetic sentinels (R1-C1).
    sentinel_key = "sk-or-v1-FAKE-DOGFOOD-SENTINEL-KEY"
    sentinel_webhook = "https://discord.com/api/webhooks/9999/FAKE-DOGFOOD-SENTINEL"
    sample["summary_text"] = f"key={sentinel_key}"
    sample["extras"] = {"webhook": sentinel_webhook}

    disk_payload = serialize_result(sample)
    screen_payload = as_display(sample)
    assert sentinel_key not in str(disk_payload), "serialize_result leaked api key"
    assert sentinel_key not in str(screen_payload), "as_display leaked api key"
    assert sentinel_webhook not in str(disk_payload), "serialize_result leaked webhook"
    assert sentinel_webhook not in str(screen_payload), "as_display leaked webhook"

    print("dogfood smoke OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
