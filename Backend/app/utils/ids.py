from __future__ import annotations
import re
import time
import secrets

RUN_ID_RE = re.compile(r"^RUN_[A-Z0-9]{26,40}$")


def generate_run_id() -> str:
    # ULID-like: timestamp + random (simple, sin dependencia externa)
    ts = int(time.time() * 1000)
    rnd = secrets.token_hex(10).upper()  # 20 hex chars
    return f"RUN_{ts:X}{rnd}"


def is_valid_run_id(run_id: str) -> bool:
    return bool(RUN_ID_RE.match(run_id))
