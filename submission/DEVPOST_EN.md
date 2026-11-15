# CourseJesus — AccessBridge

## Inspiration

CourseJesus already helps university learners study course material through
retrieval, knowledge maps, questions, and generated visuals. AccessED exposed a
different question: can the same learning experience remain usable when a
student needs bilingual explanations, keyboard navigation, large text, clear
source provenance, a non-visual equivalent of a diagram, or an offline copy?

We treated accessibility as part of the learning path rather than a separate
mode. The competition work is called **CourseJesus — AccessBridge**.

## What it does

The existing CourseJesus site is the experience. Public visitors receive an
isolated guest workspace, can browse authorized public courses, and can use the
new AccessBridge learning route. They cannot see private courses, owner
identifiers, learner records, grades, profiles, or administrative controls.

The API-independent public judging surface is available at
<https://coursejesus-accessbridge.netlify.app/>. It runs the same accessible
AccessBridge component as the complete competition build and needs no account,
backend service, model, GPU, or private learner data. The complete guest shell
and its FastAPI visitor-isolation boundary are verified in the source copy and
run locally; the static host does not pretend to be that full-stack service.

AccessBridge currently includes three original bilingual lessons:

- stack and queue order;
- breadth-first versus depth-first traversal; and
- homogeneous matrix transforms with scale, rotation, then translation.

Each lesson has stepped explanations, a deterministic accessible SVG, a long
text equivalent, visible source labels, a language switch, large text, three
practice questions, answer-specific feedback, and a self-contained offline
practice download.

The BFS/DFS and matrix examples are computed from explicit graph and matrix
data. The interface does not trust a stored quiz answer index to decide which
visual path or coordinate is correct.

## How we built it

The project starts from the real CourseJesus source at application commit
`f195990b9e4a280d92be60bcf1e205dce032db95`. We created an isolated competition
copy and reused individually reviewed VisualSpec/compiler/validator components
associated with `coursemate-ai@1074b61`.

During the competition we added:

- signed, expiring public guest sessions with a `guest_` subject namespace;
- an explicit guest API method/path allowlist;
- browser-scoped guest authority and complete-shell guest UI states;
- the integrated `Learn` route and three accessible lessons;
- deterministic accessible diagrams and text equivalents;
- bilingual controls, large text, source expansion, and offline practice;
- guest retention cleanup;
- frontend, backend, HTTP, build, and real-Chrome acceptance tests.

The local safe demo uses an empty isolated SQLite database, deterministic RAG,
mock/local visual boundaries, and independent runtime paths. It does not call
production RAG, Agent, Qwen, ComfyUI, EAS, GPU, or private media.

## Accessibility

The tested pages support keyboard focus and activation, semantic headings,
radio groups, status/feedback text, non-colour labels, 360/390/768 px layouts,
and a 640 CSS-pixel equivalent 200% reflow check. Real Chrome axe scans reported
zero WCAG A/AA violations on the tested surfaces. That result is evidence for
those pages; it is not a claim of full WCAG certification.

The offline HTML contains only the selected exported lesson and practice. It
does not claim offline AI, does not create new instruction, and does not award an
official grade or change CourseJesus learning authority.

## Three learning barriers

### 1. Reading without active practice

Before: a learner could read a generated explanation without a quick way to
test the sequence or calculation.

After: each AccessBridge lesson includes three short questions with immediate,
answer-specific explanations. The result is practice only and is not presented
as an official certification score.

### 2. No visible learning structure

Before: it was harder to see how an explanation, source, visual, and practice
fit together.

After: the AccessBridge route presents the lesson order, deterministic diagram,
source disclosure, text equivalent, and practice in one learning flow inside the
complete CourseJesus shell.

### 3. Visuals without an accessible equivalent

Before: diagram-only explanations excluded keyboard, large-text, bilingual, and
non-visual access paths.

After: every example pairs its SVG with semantic title/description, a long text
equivalent, visible labels, and keyboard-operable controls.

## Challenge and honest boundaries

The hard part was preserving the complete CourseJesus application while adding
public access boundaries. A public visitor needs enough state for practice, but
must never become a real student or touch production data. We therefore tested
two independent guest contexts against a separate database and rejected
cross-guest reads.

This source snapshot is **not submission-ready as a complete three-mode live
demo**. The owner still needs to create the representative course and knowledge
point, after which the team must verify course, tree, current live image/video,
historical visual, practice, and feedback in one recorded flow. Production RAG
and Agent E2E, authenticated production account isolation, public full-stack
hosting, a public GitHub release, human educator review, and measured learning
improvement are not claimed.

The official AccessED rules were re-read on 2026-11-15. The recorded deadline is
2026-11-21 06:00 UTC+8. Entrants must be students above the legal age of
majority and satisfy geographic eligibility. The final owner declaration remains
required.

## What's next

The next milestone is a representative-course E2E with a visibly separate
current generation and historical work. After that, the same build should be
published under an independent full-stack URL, tested anonymously, packaged
with rights-retained source, and submitted only after the owner confirms current
rules, eligibility, and final identity declarations.

## Built with

React, TypeScript, Vite, FastAPI, Python, SQLite, accessible SVG, Playwright,
axe-core, pytest, and Vitest. CourseJesus's pre-existing RAG, Agent,
knowledge-map, question, Canvas, and visual systems form the product foundation.

