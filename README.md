# CourseJesus AccessED Hacks competition copy

This directory is an isolated competition copy prepared for AccessED Hacks. It
starts from CourseJesus application commit
`f195990b9e4a280d92be60bcf1e205dce032db95` and keeps the original product
worktree, production database, uploads, credentials, and deployment untouched.

Current delivery state: **PARTIAL / NOT_SUBMISSION_READY / NOT_SUBMITTED**.

Public deterministic judging entry:
<https://coursejesus-accessbridge.netlify.app/>

Public source branch:
<https://github.com/xiao18825501901-rgb/coursejesus-accessbridge/tree/full-coursejesus-app-20261115>

Public release:
<https://github.com/xiao18825501901-rgb/coursejesus-accessbridge/releases/tag/accessed-hacks-submission-20261115>

The public site is an accessible static presentation of the same AccessBridge
component integrated into this complete CourseJesus source copy. It needs no
account, API server, private learner data, model, or GPU. The complete guest
shell and its FastAPI isolation boundary run locally from this repository. The
static host does not claim to provide the production RAG/Agent stack.

## What this copy adds

- A signed, expiring guest session boundary for public visitors.
- A read-only public course view that excludes private courses, owner IDs, and
  host management operations.
- Independent guest workspaces for browser-scoped practice and history.
- An integrated `Learn` route in the complete CourseJesus shell with three
  synthetic bilingual lessons: stack/queue, breadth-first/depth-first search,
  and homogeneous matrix transforms.
- Deterministic accessible SVG diagrams, text equivalents, source disclosure,
  keyboard operation, large text, English/Chinese switching, quiz feedback, and
  a self-contained offline practice download.
- Browser, API, security, build, and retention tests in the isolated copy.
- A public, API-independent judging entry for the integrated AccessBridge
  lessons.

The pre-existing CourseJesus product remains the foundation. This copy does not
claim that its historical RAG, Agent, Canvas, knowledge-tree, or visual
generation code was written during the competition.

## Requirements

- Windows PowerShell
- Node.js `24.14.0` or newer
- Python `3.11`
- Google Chrome for the native-browser acceptance test

Dependencies are installed inside this competition directory. Do not run
installation, builds, tests, migrations, or servers in the original CourseJesus
worktree.

## Start locally

```powershell
cd E:\Hackathon-2026\coursejesus-full-competition
.\scripts\start_competition.ps1
```

Open <http://127.0.0.1:15273/ui-extension/>.

The API binds only to `127.0.0.1:15274`. Its database, uploads, UI state, cache,
and logs live under `runtime/competition-local/`, which is excluded from Git and
release packages.

Stop it with:

```powershell
.\scripts\stop_competition.ps1
```

The stop script verifies command-line markers and listener ownership before it
stops a process.

## Rebuild

```powershell
npm --workspace '@coursemate/web' run build
```

The production output is `apps/web/dist/`. The build runs the repository's
personal-access-token bundle scan after Vite completes.

## Tests

```powershell
Set-Location apps\web
..\..\node_modules\.bin\vitest.cmd run --pool=threads --maxWorkers=1

Set-Location ..\..\services\rag-api
..\..\.venv\Scripts\python.exe -m pytest -q `
  tests\test_public_guest_session.py `
  tests\test_ui_extension_integration.py `
  tests\test_ui_extension_openapi.py `
  tests\test_ui_extension_cors.py `
  tests\test_visual_api_integration.py

Set-Location ..\..
.\node_modules\.bin\playwright.cmd test `
  --config=playwright.competition.config.ts
```

Final per-run results are recorded under `evidence/`. Historical results from
the standalone three-lesson AccessBridge demo are not evidence for this full
application copy.

## Package

After committing the final tree:

```powershell
.\scripts\package_submission.ps1 -Version 20261115
.\.venv\Scripts\python.exe .\scripts\make_hash_manifest.py --include-submission-artifacts
```

This writes the source ZIP, demo ZIP, `SHA256SUMS.txt`, and the hash manifest
under `submission/` and `evidence/`. Runtime directories, dependencies,
credentials, databases, uploads, private media, and review-only inputs are
excluded.

## Public visitor boundary

Guests use an HMAC-signed token with a `guest_` subject namespace. The token is
held in `sessionStorage`, expires automatically, and is accepted only by the
UI-extension method/path allowlist. Guest requests cannot use host product APIs
or authenticate as a real learner. The public shell hides creation, import,
upload, pinning, discussion, notification, profile, settings, and administrative
controls.

The local smoke fixture contains one public synthetic course and one private
synthetic course. Two guest contexts receive distinct subjects. The synthetic
fixtures prove the isolation behavior; they are not the owner's representative
course.

## Offline practice

The lesson page can export one self-contained HTML practice file. The file
contains only that selected lesson, its source labels, and its practice
questions. It is not offline AI, does not generate new material, does not store
results in CourseJesus, and does not create an official grade or certification.

## Verified and unverified boundaries

Verified locally and in the bundled browser evidence:

- Production frontend build and bundle security scan.
- Frontend behavior and backend guest-session regression tests.
- Real Chrome against the isolated production build and FastAPI UI extension.
- Public/private course visibility, two-guest isolation, keyboard operation,
  bilingual controls, large text, 390/640/768 px layouts, zero axe
  WCAG A/AA violations on the tested surfaces, and offline `file://` practice.
- Local start and stop scripts with independent ports and data directories.
- Anonymous Chromium access to the public AccessBridge entry, with three
  lessons, large text, expandable sources, a downloaded self-contained practice
  page, zero console errors, zero failed requests, and no API dependency.

Not verified or not completed:

- `BLOCKED_OWNER`: the owner-created representative course and knowledge point.
- `NOT_RUN`: the real three-mode flow of course, tree, live image/video,
  practice, answer judgment, and feedback.
- `NOT_RUN`: separating current live generation from historical generation.
- `NOT_RUN`: live Qwen, ComfyUI, EAS, GPU, model, or remote-media generation.
- `NOT_RUN`: production RAG/Agent end-to-end behavior from this copy.
- `NOT_RUN`: authenticated production two-account isolation. Two anonymous guest
  contexts were tested instead.
- `NOT_RUN`: human educator review, learning-outcome research, or a claim that
  learning improves.
- `UNKNOWN`: full WCAG certification. Automated axe checks are not a
  certification.
- `BLOCKED_ACCOUNT`: public full-stack hosting requires an existing free runtime
  account that can serve the FastAPI guest API. The public static entry is
  `VERIFIED_LIVE`; it is not evidence for the full-stack production flow.
- `NOT_SUBMITTED`: Devpost.
- `VERIFIED_LIVE`: AccessED rules were re-read on 2026-11-15. The deadline is
  `2026-11-21 06:00 UTC+8`. Entrants must be students above the legal age of
  majority and satisfy geographic eligibility. Entries must distinguish event
  work from pre-existing work, credit third parties and AI assistance, use
  permission-cleared material, and require no private judge information.

## Source and rights

The owner authorized public source publication with rights retained. No MIT or
Apache license is applied to owner-authored code. Judges may download, install,
and run this competition copy for evaluation. Third-party software retains its
own license. See `LICENSE_NOTES.md`, `THIRD_PARTY_NOTICES.md`, and
`evidence/SOURCE_MAP.json`.

## Evidence map

- `evidence/final-build-results.txt`
- `evidence/final-frontend-test-results.txt`
- `evidence/backend-test-results.txt`
- `evidence/browser-test-results.txt`
- `evidence/browser-checks.json`
- `evidence/local-start-verification.json`
- `evidence/local-stop-verification.json`
- `evidence/guest-context-isolation.json`
- `evidence/npm-audit-final-results.json`
- `evidence/pip-check-results.txt`
- `evidence/security-scan-results.json`
- `evidence/LIVE_ACCESS_EVIDENCE.json`
- `scripts/verify_live_accessbridge.mjs`
- `evidence/RULES_READBACK.json`
- `evidence/demo-captioned.mp4`
- `evidence/demo-captions.srt`
- `evidence/screenshots/`
- `submission/DEVPOST_EN.md`
- `submission/CONTRIBUTIONS.md`
- `submission/MANUAL_OWNER_ACTIONS.md`
- `submission/PUBLIC_RELEASE.md`

