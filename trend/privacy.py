from __future__ import annotations

import hashlib
import os
import re

_DEFAULT_SALT = "trend-signal-local-salt"


def mask_user(username: str | None, salt: str | None = None) -> str | None:
    if not username:
        return None
    salt = salt or os.getenv("MASK_SALT", _DEFAULT_SALT)
    h = hashlib.sha256(f"{salt}|{username.strip().lower().lstrip('@')}".encode()).hexdigest()
    return f"u_{h[:10]}"


_MENTION = re.compile(r"@\w{1,30}")


def mask_mentions(text: str, salt: str | None = None) -> str:
    return _MENTION.sub(lambda m: "@" + (mask_user(m.group(0), salt) or ""), text)
