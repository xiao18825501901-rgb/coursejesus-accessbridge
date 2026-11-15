# CourseJesus AccessED Hacks contribution disclosure

## Pre-existing CourseJesus foundation

The following platform capabilities existed before this competition session and
are part of the submitted product context:

- The complete CourseJesus web application and product design.
- RAG ingestion, retrieval, question support, and learning interfaces.
- Agent service and provider routing.
- Knowledge-map and question-generation workflows.
- VisualSpec, validators, compiler, visual-job, Qwen, and ComfyUI integration.
- Canvas import and local bridge.
- Authentication, administrative, and user-data boundaries.
- Brand assets and the existing public product domain.

No claim is made that this historical foundation was written from scratch
during AccessED Hacks.

## Competition-period work in this copy

| Area | Competition-period contribution | Evidence |
|---|---|---|
| Public access | Added signed, expiring guest sessions in a `guest_` namespace | `services/rag-api/app/ui_extension/guest.py`; `tests/test_public_guest_session.py` |
| Guest authorization | Added a method/path allowlist and excluded host/admin APIs | `services/rag-api/app/ui_extension/guest.py`; `tests/test_public_guest_session.py` |
| Browser storage | Scoped guest authority to `sessionStorage` | `apps/web/src/guestSession.ts`; `guestSession.test.ts` |
| Public UI | Hid create, import, upload, pin, discussion, notification, profile, settings, and admin controls from guests | `CourseMateUi.tsx`; `PublicGuestUi.test.tsx` |
| Learning route | Integrated a `Learn` entry and `#/accessbridge` route into the complete shell | `App.jsx`; `AccessBridgeDemo.jsx` |
| Lesson content | Added original bilingual stack/queue, BFS/DFS, and matrix-transform lessons | `apps/web/src/competition/` |
| Visual reasoning | Computed search order and matrix results from explicit graph/matrix data rather than trusting quiz answer indexes | `lessonLogic.js`; lesson tests |
| Accessibility | Added keyboard operation, large text, bilingual content, source expansion, text equivalents, responsive reflow, and accessible SVG | `AccessBridgeDemo.jsx`; `AccessBridgeDiagram.jsx`; browser evidence |
| Practice | Added three questions and rationales per lesson plus self-contained offline practice export | `AccessBridgeDemo.jsx`; browser evidence |
| Retention | Added expired guest-workspace pruning and an operator command | `guest.py`; `scripts/purge_expired_guest_data.py` |
| Verification | Added frontend, backend, HTTP isolation, build, and real-Chrome acceptance tests | `evidence/` |
| Public judging entry | Added an API-independent static entry using the same integrated AccessBridge component and published it under an independent Netlify site | `apps/web/accessbridge.html`; `apps/web/src/main.accessbridge.tsx`; `netlify.competition.toml` |
| Documentation | Added source map, license notes, data boundaries, Devpost draft, screenshots, and operator card | `README.md`; `submission/` |

## Reused source

The complete application baseline is
`coursemate-ai@f195990b9e4a280d92be60bcf1e205dce032db95`. The reviewed visual
components originate from `coursemate-ai@1074b61`:

- `services/rag-api/app/visual/spec.py`
- `services/rag-api/app/visual/validators.py`
- `services/rag-api/app/visual/compiler.py`

Exact hashes and local dispositions are in `evidence/SOURCE_MAP.json`.

CleanRebuild `5b622b9d0bfde519cd3eb34e7229dbbcbbfcea5b` was inspected and not
used as an application base because it is NanoJev research tooling.

## AI assistance

OpenAI Codex supported code changes, tests, documentation, screenshots, and
review in this competition copy. The owner remains responsible for identity,
eligibility, representative-course content, final rights declarations, public
account decisions, and final submission.

## Not claimed

No claim is made for live production generation, representative-course
end-to-end completion, authentic student-data isolation, human educator review,
measured learning improvement, full WCAG certification, public full-stack
hosting, a refreshed public repository Release, or Devpost submission until
their respective evidence exists. The API-independent static judging entry is
separately `VERIFIED_LIVE`.

