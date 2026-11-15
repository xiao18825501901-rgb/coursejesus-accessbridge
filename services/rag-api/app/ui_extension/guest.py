"""Short-lived public visitor sessions for the mounted CourseJesus UI.

Guest tokens are signed with an HMAC secret held by the backend. They are
accepted only by the UI extension: ordinary host APIs continue to use Clerk or
the explicitly test-only verifier. Each token names an independent subject and
expires automatically, so client-supplied owner IDs are never trusted.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import re
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from fastapi import Request

_TOKEN_PREFIX = "cjg1"
_NAMESPACE_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GUEST_RETENTION_GRACE_SECONDS = 60 * 60


class GuestSessionError(ValueError):
    """The bearer value is not a current, valid guest session."""


@dataclass(frozen=True)
class GuestSession:
    subject: str
    expires_at: int


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode(value + padding)


class GuestSessionAuthority:
    """Issue and verify namespaced bearer tokens without server-side state."""

    def __init__(
        self,
        secret: str,
        ttl_seconds: int,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        secret_bytes = secret.encode("utf-8")
        if len(secret_bytes) < 16:
            raise ValueError("Guest session secret must contain at least 16 bytes.")
        if not 60 <= ttl_seconds <= 7 * 24 * 60 * 60:
            raise ValueError("Guest session lifetime must be between 60 seconds and 7 days.")
        self._key = hmac.new(
            secret_bytes,
            b"coursejesus-guest-session-v1",
            hashlib.sha256,
        ).digest()
        self.ttl_seconds = ttl_seconds
        self._clock = clock

    @staticmethod
    def bearer_token(request: Request) -> str | None:
        authorization = request.headers.get("authorization", "")
        if not authorization.startswith("Bearer "):
            return None
        token = authorization[7:].strip()
        return token or None

    def issue(self) -> dict[str, object]:
        now = int(self._clock())
        expires_at = now + self.ttl_seconds
        payload = {
            "exp": expires_at,
            "iat": now,
            "kind": "guest",
            "nonce": secrets.token_urlsafe(18),
            "sub": "guest_" + secrets.token_hex(32),
        }
        encoded = _b64encode(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        signature = hmac.new(
            self._key,
            f"{_TOKEN_PREFIX}.{encoded}".encode("ascii"),
            hashlib.sha256,
        ).digest()
        return {
            "token": f"{_TOKEN_PREFIX}.{encoded}.{_b64encode(signature)}",
            "expires_at": expires_at,
            "expires_in_seconds": self.ttl_seconds,
            "session_kind": "guest",
        }

    def verify(self, token: str) -> GuestSession:
        try:
            prefix, encoded, supplied_signature = token.split(".")
            if prefix != _TOKEN_PREFIX or not encoded or not supplied_signature:
                raise ValueError
            expected = hmac.new(
                self._key,
                f"{prefix}.{encoded}".encode("ascii"),
                hashlib.sha256,
            ).digest()
            supplied_signature_bytes = _b64decode(supplied_signature)
            if _b64encode(supplied_signature_bytes) != supplied_signature:
                raise ValueError
            if not hmac.compare_digest(expected, supplied_signature_bytes):
                raise ValueError
            payload_bytes = _b64decode(encoded)
            if _b64encode(payload_bytes) != encoded:
                raise ValueError
            payload = json.loads(payload_bytes.decode("utf-8"))
            if not isinstance(payload, dict) or payload.get("kind") != "guest":
                raise ValueError
            now = int(self._clock())
            issued_at = int(payload["iat"])
            expires_at = int(payload["exp"])
            subject = payload["sub"]
            nonce = payload["nonce"]
            if (
                not isinstance(subject, str)
                or not subject.startswith("guest_")
                or not _NAMESPACE_PATTERN.fullmatch(subject[6:])
                or not isinstance(nonce, str)
                or len(nonce) < 20
                or issued_at > now + 30
                or expires_at <= now
                or expires_at <= issued_at
            ):
                raise ValueError
        except (
            UnicodeDecodeError,
            ValueError,
            TypeError,
            KeyError,
            binascii.Error,
            json.JSONDecodeError,
        ) as error:
            raise GuestSessionError("Invalid or expired guest session.") from error
        return GuestSession(subject=subject, expires_at=expires_at)

    def request_session(self, request: Request) -> GuestSession | None:
        token = self.bearer_token(request)
        if token is None:
            return None
        try:
            return self.verify(token)
        except GuestSessionError:
            return None


def prune_expired_guest_data(
    database: object,
    ttl_seconds: int,
    *,
    clock: Callable[[], float] = time.time,
) -> int:
    """Delete guest-owned UI rows after the token lifetime plus a one-hour grace.

    Guest tokens are stateless. The UI database records the subject's creation
    time when the first request arrives, so a bounded age removes dormant guest
    workspaces without affecting verified users. The function is safe to call on
    every guest-token issuance and from an operator's scheduled cleanup job.
    """

    cutoff = datetime.fromtimestamp(
        clock() - ttl_seconds - _GUEST_RETENTION_GRACE_SECONDS,
        tz=timezone.utc,
    ).isoformat(timespec="milliseconds")
    with database.connect(write=True) as connection:  # type: ignore[attr-defined]
        subjects = [
            str(row["id"])
            for row in connection.execute(
                "SELECT id FROM cmui_users "
                "WHERE id LIKE 'guest_%' AND created_at<? ORDER BY created_at",
                (cutoff,),
            ).fetchall()
        ]
        if not subjects:
            return 0
        markers = ",".join("?" for _ in subjects)

        # Child rows are removed before their users. Some historical tables use
        # NO ACTION rather than cascade, so the order below is significant.
        for table in (
            "cmui_answer_reveals",
            "cmui_exercises",
            "cmui_compact_pair_links",
            "cmui_node_starts",
            "cmui_pairs",
            "cmui_bridges",
            "cmui_agent_receipts",
            "cmui_runs",
            "cmui_conversations",
            "cmui_sessions",
            "cmui_layout",
            "cmui_preferences",
            "cmui_learning",
            "cmui_limits",
            "cmui_pins",
            "cmui_verification",
        ):
            connection.execute(
                f"DELETE FROM {table} WHERE owner IN ({markers})",
                subjects,
            )
        connection.execute(
            f"DELETE FROM cmui_directory WHERE subject IN ({markers})",
            subjects,
        )
        connection.execute(
            f"DELETE FROM cmui_users WHERE id IN ({markers})",
            subjects,
        )
    return len(subjects)


_GUEST_ROUTES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("GET", re.compile(r"^/me$")),
    ("GET", re.compile(r"^/me/verification$")),
    ("GET", re.compile(r"^/me/preferences$")),
    ("PUT", re.compile(r"^/me/preferences$")),
    ("GET", re.compile(r"^/courses$")),
    ("GET", re.compile(r"^/courses/[^/]+$")),
    ("GET", re.compile(r"^/courses/[^/]+/files$")),
    (
        "GET",
        re.compile(r"^/courses/[^/]+/files/[^/]+/(?:content|text)$"),
    ),
    ("GET", re.compile(r"^/courses/[^/]+/knowledge$")),
    ("GET", re.compile(r"^/courses/[^/]+/knowledge-build-status$")),
    ("GET", re.compile(r"^/courses/[^/]+/layout$")),
    ("PUT", re.compile(r"^/courses/[^/]+/layout$")),
    ("POST", re.compile(r"^/courses/[^/]+/nodes/[^/]+/open$")),
    ("POST", re.compile(r"^/courses/[^/]+/exercises$")),
    (
        "GET",
        re.compile(r"^/courses/[^/]+/knowledge/[^/]+/assessment(?:/.*)?$"),
    ),
    (
        "POST",
        re.compile(r"^/courses/[^/]+/knowledge/[^/]+/assessment(?:/.*)?$"),
    ),
    (
        "GET",
        re.compile(r"^/courses/[^/]+/knowledge/assessment/[^/]+(?:/.*)?$"),
    ),
    (
        "POST",
        re.compile(r"^/courses/[^/]+/knowledge/assessment/[^/]+(?:/.*)?$"),
    ),
    ("GET", re.compile(r"^/conversations$")),
    ("POST", re.compile(r"^/conversations$")),
    ("GET", re.compile(r"^/conversations/[^/]+$")),
    ("PATCH", re.compile(r"^/conversations/[^/]+$")),
    ("POST", re.compile(r"^/conversations/[^/]+/runs$")),
    ("GET", re.compile(r"^/runs/[^/]+$")),
    ("GET", re.compile(r"^/runs/[^/]+/events$")),
    ("POST", re.compile(r"^/runs/[^/]+/cancel$")),
    ("GET", re.compile(r"^/pairs$")),
    ("POST", re.compile(r"^/pairs$")),
    ("GET", re.compile(r"^/pairs/[^/]+$")),
    ("PATCH", re.compile(r"^/pairs/[^/]+$")),
    ("DELETE", re.compile(r"^/pairs/[^/]+$")),
    ("POST", re.compile(r"^/pairs/[^/]+/bind$")),
    ("GET", re.compile(r"^/exercises/[^/]+$")),
    ("POST", re.compile(r"^/exercises/[^/]+/reveal$")),
    ("POST", re.compile(r"^/exercises/[^/]+/hints$")),
    ("POST", re.compile(r"^/exercises/[^/]+/attempts$")),
    ("POST", re.compile(r"^/exercises/[^/]+/steps/[^/]+/explanation$")),
    ("GET", re.compile(r"^/explanations/[^/]+$")),
    ("POST", re.compile(r"^/explanations/[^/]+/messages$")),
    ("POST", re.compile(r"^/explanations/[^/]+/cancel$")),
    ("GET", re.compile(r"^/courses/[^/]+/visual-assistance$")),
    ("PUT", re.compile(r"^/courses/[^/]+/visual-assistance$")),
    ("GET", re.compile(r"^/courses/[^/]+/messages/[^/]+/visuals$")),
    ("POST", re.compile(r"^/courses/[^/]+/messages/[^/]+/visuals$")),
    ("GET", re.compile(r"^/courses/[^/]+/pairs/[^/]+/visuals$")),
    ("GET", re.compile(r"^/visual-jobs/[^/]+$")),
    ("POST", re.compile(r"^/visual-jobs/[^/]+/(?:cancel|retry|fallback)$")),
    ("GET", re.compile(r"^/visual-assets/[^/]+/content$")),
    ("HEAD", re.compile(r"^/visual-assets/[^/]+/content$")),
    ("GET", re.compile(r"^/courses/[^/]+/legacy-conversations(?:/[^/]+)?$")),
)


def guest_operation_allowed(method: str, api_path: str) -> bool:
    """Return whether a guest may reach this UI-extension operation."""

    normalized_method = method.upper()
    return any(
        normalized_method == allowed_method and pattern.fullmatch(api_path)
        for allowed_method, pattern in _GUEST_ROUTES
    )
