# CourseJesus — AccessBridge

A self-contained, accessible teaching demo for **AccessED Hacks**. It turns a
validated CourseJesus `VisualSpec 1.0` object into a bilingual lesson with a
deterministic SVG diagram, a visible source trail, three short practice
questions, and a single-file offline pack that opens with no server and no
network.

Everything in this folder is an isolated competition copy. No production
CourseJesus service, database, model, GPU, or private media is contacted at any
point.

## Status

| Area | State |
| --- | --- |
| Three original lessons, English + Chinese | Working, `VERIFIED_LOCAL` |
| Deterministic VisualSpec 1.0 → SVG compiler | Working, byte-identical rebuilds |
| Accessible UI (keyboard, ARIA, 200% reflow, mobile) | Working, automated browser checks pass |
| Single-file offline practice packs | Working, opens from `file://` with the network off |
| Test suite | 33 passed, 0 failed |
| Public demo URL | Not deployed — `BLOCKED` on owner hosting decision |
| Devpost submission | Not submitted — owner action |

## Run it

Windows PowerShell, from this folder:

```powershell
.\scripts\start.ps1
```

The script builds the site, starts a loopback-only server on port `15273`, and
waits for a health check. Then open <http://127.0.0.1:15273/>.

```powershell
.\scripts\stop.ps1
```

Stops only the process recorded in `runtime\server.pid`, and only if that
process is this project's server. Logs land in `runtime\`.

For a foreground run with live output:

```powershell
.\scripts\run.ps1
```

The offline packs need no server at all: open
`app\dist\offline\stack-queue.html` (or `bfs-dfs.html`, `matrix-transform.html`)
directly from disk.

## First-time setup

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m playwright install chromium
```

Runtime code needs only `pydantic`. `pytest` and `playwright` are used by the
test suite.

## What the demo shows

Three lessons ship as original synthetic fixtures:

1. **Stacks and queues** — LIFO versus FIFO removal order.
2. **Breadth-first and depth-first search** — a five-node directed graph with explicit alphabetical neighbour order.
3. **Matrix transforms** — scale, then rotate, then translate.

Each lesson page has the same structure: a bilingual one-step-at-a-time
explanation, a compiled SVG with a long text description, a glossary, three
practice questions with source-linked feedback, and an expandable source panel.
The language button swaps every localized string, including the SVG `<title>`
and `<desc>`; the text-size button raises the base size to 22px.

The offline page is a single HTML file with inline CSS and JavaScript. It
contains the same steps, diagram, and practice, and states on the page that
practice is not an official grade.

## How the pipeline works

```
fixtures/lessons/*.json
        │  app/lessons.py            strict schema: bilingual text, sources, 3 quiz items
        ▼
VisualSpec 1.0 object
        │  app/visual/router.py      deterministic-only router
        ▼
app/visual/compiler.py               layered DAG layout → escaped, anchored SVG
        │  app/visual/validators.py  SVG allowlist + size/safety checks
        ▼
app/site.py                          online pages, offline pages, manifest.json
        │  app/offline_export.py → app/offline_pack.py
        ▼
app/dist/                            8 files, hashed in dist/manifest.json
```

Compilation is pure Python with no network access. The same lesson fixture
always produces the same SVG string, and `tests/test_build_determinism.py`
rebuilds the whole site twice and compares bytes.

## Verify it

```powershell
.\.venv\Scripts\python.exe -m app.build
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\make_evidence.py
```

`make_evidence.py` rewrites `evidence\HASH_MANIFEST.json` and
`evidence\RESULTS.json` from the files on disk. The browser test writes
`evidence\browser-checks.json` and refreshes the screenshots in
`evidence\screenshots\`.

Local results at the time of packaging are recorded in `evidence\RESULTS.json`:
33 tests passed, 22 browser checks passed, zero axe WCAG violations on the
index and lesson pages, zero external network requests, zero page or console
errors.

## Provenance

The visual engine is imported from CourseJesus `coursemate-ai` at commit
`1074b612db87c97c9caff09b5a32bcc5360d7de0`:

- `services/rag-api/app/visual/spec.py`
- `services/rag-api/app/visual/validators.py`
- `services/rag-api/app/visual/compiler.py`

Exact byte copies live in `source-visual-1074/`. `app/visual/compiler_original.py`
is the unmodified upstream compiler kept for comparison; `app/visual/compiler.py`
is the competition compiler that renders a tight `viewBox`, adds `<title>`,
`<desc>`, `role="img"` and bilingual metadata. The offline pack renderer derives
from the handoff package's `offline_pack.py`. Per-file hashes and modification
notes are in `evidence\SOURCE_MAP.json`.

The `CleanRebuild 5b622b9` tree was inspected and excluded: it contains the
NanoJev research tooling, not a compatible CourseJesus application scaffold.

## Boundaries

This build does **not**:

- call RAG, the Agent service, Qwen, ComfyUI, EAS, or a GPU;
- generate images or video at runtime, or claim a live model path;
- read or write CourseJesus learner scores, the `LEARNED` authority, or any
  production database;
- store learner data — practice results live only in page memory;
- present practice as certification or an official course grade.

`evidence\DATA_BOUNDARIES.md` lists what data the app touches and what it
deliberately does not copy. `submission\MANUAL_OWNER_ACTIONS.md` lists the
remaining actions that only the project owner can take.

## Layout

| Path | Purpose |
| --- | --- |
| `app/` | lessons schema, visual engine, site generator, offline pack, server |
| `fixtures/lessons/` | three original lesson sources |
| `tests/` | schema, determinism, semantics, security, server, browser |
| `scripts/` | start, stop, foreground run, demo recording, evidence rebuild |
| `evidence/` | results, hash manifest, source map, screenshots, video |
| `submission/` | Devpost copy, contributions, screenshot guide, owner actions |
| `source-visual-1074/` | unmodified upstream visual source for provenance |

## Rights and public release

Public demo: https://coursejesus-accessbridge.netlify.app/

Source-available, rights retained. LICENSE explicitly permits event judges to
download, install and run this competition version for evaluation. Owner
decisions are recorded in OWNER_DECISIONS.json. Third-party licenses remain
in force. No historical upstream license is invented. This is not open source.

For Linux/macOS: create a Python 3.11+ virtual environment, install
requirements-dev.txt, then `python -m app.build` and
`python -m app.server --host 127.0.0.1 --port 15273`. Install a test browser with
`python -m playwright install chromium`; browser tests use CHROME_PATH, system
Chromium/Chrome or Playwright Chromium. Windows launch scripts remain supported.

Local Python supplies /healthz; the public static site does not need it.
See submission/FINAL_DELIVERY.json for current test/public-release state.
