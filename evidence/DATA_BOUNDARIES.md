# Data boundaries and isolation evidence

## Competition-local runtime

The local launcher sets these boundaries:

| Purpose | Competition-local location/configuration |
|---|---|
| Web origin | `http://127.0.0.1:15273` |
| API origin | `http://127.0.0.1:15274` |
| RAG database | `runtime/competition-local/data/rag.sqlite3` |
| RAG uploads | `runtime/competition-local/data/uploads` |
| UI-extension database | `runtime/competition-local/data/ui-extension/ui.sqlite3` |
| Logs | `runtime/competition-local/logs` |
| Provider mode | deterministic/mock |
| Visual generation | mock, automatic creation disabled, video disabled |
| Knowledge-map automation | disabled |

No competition script reads the original CourseJesus `.env`, database, uploads,
model weights, browser session, or production credentials.

## Guest authority

- The backend issues a signed token whose subject starts with `guest_`.
- The signing secret is generated or supplied only inside the isolated runtime.
- The token expires after a short configured lifetime.
- The browser holds the token in `sessionStorage`, not `localStorage` or a
  cookie.
- Guest access is limited by an explicit HTTP method and path allowlist.
- A guest cannot call host product APIs, create courses, mutate users/admin
  state, or claim a real user ID.
- Public course responses omit owner identifiers.

## Synthetic smoke result

The local HTTP smoke check seeded one public and one private synthetic course.
It then exercised two independent guest sessions. `evidence/local-smoke.json`
records:

- Two distinct guest sessions.
- One public course visible.
- Private course unavailable (`404`).
- Guest cannot create a course (`403`).
- Guest B cannot read Guest A's pair (`404`).
- No owner IDs exposed.

These are isolation fixtures. They do not establish that the owner's eventual
representative course has been verified.

## Retention

Expired guest workspaces are deleted after the token lifetime plus a one-hour
grace period. Cleanup runs when a new guest session is issued, and
`scripts/purge_expired_guest_data.py` provides the same bounded cleanup for a
platform scheduler. The script and database API were not connected to a
production scheduler in this delivery.

## Excluded material

Release ZIPs exclude `.env`, credentials, `.venv`, `node_modules`, Git metadata,
caches, `runtime/`, private review inputs, production databases, uploads, model
weights, private media, and browser state.

