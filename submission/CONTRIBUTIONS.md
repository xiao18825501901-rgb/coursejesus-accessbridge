# Existing and new contributions

Base: CourseJesus `coursemate-ai` at commit
`1074b612db87c97c9caff09b5a32bcc5360d7de0`.
Entry: `E:\Hackathon-2026\coursejesus-accessbridge`.

## Carried over from CourseJesus

| Component | Upstream path | How it is used here | Change |
| --- | --- | --- | --- |
| VisualSpec 1.0 models | `services/rag-api/app/visual/spec.py` | Defines the lesson's visual contract | None, byte-identical |
| SVG output validator | `services/rag-api/app/visual/validators.py` | Allowlist, size, animation, and URL checks before an SVG ships | `title` and `desc` added to the allowlist |
| Original visual compiler | `services/rag-api/app/visual/compiler.py` | Kept as `compiler_original.py` for comparison | None, byte-identical |
| Offline pack helper | handoff package `offline_pack.py` | Basis for the single-file offline practice page | Reworked for this lesson schema and rights/answer checks |

## New in AccessBridge

| Component | Path | Contribution |
| --- | --- | --- |
| Accessible compiler | `app/visual/compiler.py` | Content-bounded `viewBox`, escaped bilingual `<title>`/`<desc>`, `role="img"`, stable content hash |
| Deterministic router | `app/visual/router.py` | Refuses remote renderers; deterministic diagram/SVG only |
| Lesson schema | `app/lessons.py` | Bilingual text, resolvable source references, exactly three quiz items, answer bounds |
| Site generator | `app/site.py` | Index, lesson pages, offline wiring, build manifest, language and text-size controls |
| Offline export | `app/offline_export.py` | Maps lesson + compiled visual into a validated `LearningPack` |
| Offline pack renderer | `app/offline_pack.py` | Rights gate, answer validation, duplicate rejection, unsafe-SVG rejection, practice-not-a-grade notice |
| Server | `app/server.py` | Loopback-only static server with `/healthz` |
| Build CLI | `app/build.py` | Writes `app/dist` deterministically |
| Lessons | `fixtures/lessons/` | Three original synthetic lessons, each with steps, sources, glossary, and three quiz items |
| Start/stop/run scripts | `scripts/*.ps1` | PID-guarded start, safe stop, foreground run |
| Demo recorder | `scripts/record_demo.py` | Captioned browser walkthrough with burned-in subtitles |
| Evidence builder | `scripts/make_evidence.py` | Regenerates the hash manifest and results summary from files on disk |
| Tests | `tests/` | 29 tests: schema, compiler, determinism, semantics, security, server, real Chromium |
| Accessibility verification | `tests/test_browser.py`, `tests/vendor/` | axe scan, keyboard path, reflow, responsive widths, offline open, two-context isolation |

## What this build did not take from CourseJesus

- No production RAG database, upload directory, vector index, or agent database.
- No authentication, Canvas, or Clerk integration.
- No model weights, ComfyUI graphs, EAS configuration, or generated media.
- No NanoJev research components. The `CleanRebuild 5b622b9` tree was inspected
  and excluded because it is NanoJev tooling rather than an application
  scaffold.
- No production environment variables, tokens, or learner records.

## Division of work

The AccessBridge application, lessons, tests, scripts, and documentation were
written in this competition session. The visual contract and its validator come
from the existing CourseJesus codebase and are credited above.


## 2026-11-13 revision

Reviewed candidate supplied via Drive: selectively reused two revised lessons
and independent BFS/DFS/affine-transform algorithm tests. Local revisions then
aligned diagram labels, numerical column-vector stages, TRSp convention and
reverse-order quiz/rationale in both languages. The five-node directed graph
now specifies start A and alphabetical outgoing-neighbour order. Added
anonymous public-browser/download verification and portable browser discovery.

Codex/ChatGPT assisted text, translations, code, tests and documentation.
Original production repository and deployment were not edited. A clean public
competition snapshot with explicit judging permission is published separately.
