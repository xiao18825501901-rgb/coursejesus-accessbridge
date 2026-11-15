"""Exercise the local public-guest boundary over real HTTP without printing tokens."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


BASE = os.getenv("COMPETITION_WEB_URL", "http://127.0.0.1:15273").rstrip("/")
API = f"{BASE}/ui-extension/api/ui/v1"
PUBLIC_COURSE_ID = os.getenv(
    "COMPETITION_PUBLIC_COURSE_ID",
    "competition-public-course",
)
PRIVATE_COURSE_ID = os.getenv(
    "COMPETITION_PRIVATE_COURSE_ID",
    "competition-private-course",
)


def request(
    path: str,
    *,
    method: str = "GET",
    token: str | None = None,
    payload: dict[str, object] | None = None,
):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        f"{API}{path}",
        method=method,
        data=json.dumps(payload or {}).encode("utf-8") if method == "POST" else None,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def issue_guest() -> str:
    status, body = request("/guest-session", method="POST")
    if status != 200 or body.get("session_kind") != "guest" or not body.get("token"):
        raise SystemExit(f"Guest session issuance failed with HTTP {status}.")
    return str(body["token"])


def main() -> None:
    guest_a = issue_guest()
    guest_b = issue_guest()

    status, courses = request("/courses", token=guest_a)
    if status != 200:
        raise SystemExit(f"Guest course listing failed with HTTP {status}.")
    ids = [course.get("id") for course in courses]
    if ids != [PUBLIC_COURSE_ID]:
        raise SystemExit(f"Unexpected guest course visibility: {ids}")
    if any("owner" in course for course in courses):
        raise SystemExit("Guest course projection leaked an owner identifier.")

    private_status, _ = request(
        "/courses/" + PRIVATE_COURSE_ID,
        token=guest_a,
    )
    if private_status != 404:
        raise SystemExit(f"Private course was not hidden from guest: HTTP {private_status}.")

    pair_status, pair = request(
        "/pairs",
        method="POST",
        token=guest_a,
        payload={"course": PUBLIC_COURSE_ID},
    )
    if pair_status != 201:
        # The pair endpoint may require a course payload; a forbidden dependency is
        # still a failure worth surfacing rather than treating a synthetic check as passed.
        raise SystemExit(f"Guest pair creation failed with HTTP {pair_status}.")
    pair_id = pair.get("id")
    other_status, _ = request(f"/pairs/{pair_id}", token=guest_b)
    if other_status != 404:
        raise SystemExit(f"Cross-guest pair access was not denied: HTTP {other_status}.")

    forbidden_status, _ = request(
        "/courses",
        method="POST",
        token=guest_a,
    )
    if forbidden_status != 403:
        raise SystemExit(f"Guest course creation was not denied: HTTP {forbidden_status}.")

    print(
        json.dumps(
            {
                "status": "PASS",
                "guest_sessions": 2,
                "visible_public_courses": 1,
                "private_course_status": private_status,
                "cross_guest_pair_status": other_status,
                "guest_course_create_status": forbidden_status,
                "owner_ids_exposed": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
