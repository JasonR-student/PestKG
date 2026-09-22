from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from fastapi import HTTPException


def filters_fingerprint(filters: dict[str, Any]) -> str:
    payload = json.dumps(filters, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def encode_cursor(offset: int, release_id: str, filter_hash: str) -> str:
    payload = json.dumps(
        {"offset": offset, "release_id": release_id, "filter_hash": filter_hash},
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def decode_cursor(
    cursor: str | None, expected_release_id: str, expected_filter_hash: str
) -> int:
    if not cursor:
        return 0
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        offset = int(payload["offset"])
        if offset < 0:
            raise ValueError
        if payload.get("release_id") != expected_release_id:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "cursor_release_mismatch",
                    "message": "Cursor belongs to a different data release",
                },
            )
        if payload.get("filter_hash") != expected_filter_hash:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "cursor_filter_mismatch",
                    "message": "Cursor does not match the current filters",
                },
            )
        return offset
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid cursor") from exc
