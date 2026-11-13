# CourseJesus — AccessBridge

**AccessED Hacks 2026 · Education access**

## One line

AccessBridge turns a validated CourseJesus visual specification into a bilingual
lesson with an accessible diagram, a visible source trail, three short practice
questions, and a complete offline study pack that works with the network off.

## The problem

CourseJesus already produces visual explanations, but the visuals were designed
for people who can see them well, on a fast connection, in one language. A
student with low vision, a screen reader, a slow connection, or a second
language gets much less from the same lesson. Two failure modes show up
repeatedly:

1. The diagram carries meaning that the text never states, so a non-visual
   learner loses the argument the picture was making.
2. Practice depends on a live service, so a student on a plane, in a lab with a
   firewall, or on a metered connection cannot review what they already paid
   for in time and attention.

AccessBridge treats both as design constraints rather than afterthoughts.

## What it does

Three original lessons ship with the demo: stacks and queues, breadth-first
versus depth-first search, and matrix transforms.

Each lesson page gives the learner:

- **One small step at a time.** Three short steps in English and Chinese, each
  naming the source it came from, so the page never asks someone to hold a
  whole derivation in working memory at once.
- **A diagram with a text equivalent.** The SVG carries a title, a long
  description, and a bilingual text pair, and every claim in the picture also
  appears as prose.
- **A source panel.** Opening a source shows its text plus the rights note for
  that text, so a learner can check what the lesson claims.
- **Three short checks.** Each answer gets a rationale and the source id it
  rests on. The page states plainly that this is practice, not a grade.
- **A single-file offline pack.** One HTML file, inline styles and scripts, no
  server, no requests. It opens from `file://` with the network disabled.

The whole page also gets a language toggle that swaps every localized string,
including the SVG title and description, and a larger-text control that raises
the base type to 22px.

## How it works

The core is a deterministic pipeline:

```
lesson JSON  →  VisualSpec 1.0  →  deterministic compiler  →  validated SVG  →  HTML
```

The compiler takes the CourseJesus `VisualSpec 1.0` model, lays out the diagram
as a layered graph, escapes every label, and emits SVG with `role="img"`,
`<title>`, and `<desc>`. The same lesson always produces the same bytes; the
build is hash-listed and a test rebuilds the site twice and compares output.

An allowlist validator checks the SVG before it ships: only safe elements, no
event handlers, no external references, no embedded scripts, bounded size.

No model, GPU, image generator, or remote service runs at any point. The
competition build imports the reviewed visual engine from CourseJesus commit
`1074b61` and stops there.

## Accessibility work

- Semantic landmarks, one `h1` per page, and a skip link that appears on focus.
- Keyboard-only path through the language toggle, the text-size toggle, the
  quiz radios, the check buttons, and the source disclosures.
- Colour carries no meaning alone; every relation is stated in words.
- Automated axe checks found zero tested WCAG violations on the index
  and the lesson pages.
- Reflow holds at a 640 CSS-pixel viewport, the equivalent of 200% zoom on a
  1280-pixel window, with no horizontal scrolling.
- Responsive from 360px upward; tested at 360, 390, 768, and 1280.
- A content security policy that forbids every network destination, so the page
  cannot quietly phone home.

## What we verified

The local suite runs 33 tests, including a real Chromium pass that performs 22
checks: keyboard navigation, language switching, wrong-answer feedback, source
expansion, 200% reflow, four viewport widths, an axe scan, an offline open with
the network disabled, and a two-context check that no learner state leaks
between browser profiles.

Evidence lives in the repository: `evidence/RESULTS.json`,
`evidence/browser-checks.json`, screenshots at desktop and mobile widths, and a
captioned two-minute walkthrough.

## Challenges

The hardest part was keeping the visual honest. A diagram that looks good but
adds a claim the source never made is worse than no diagram, so the compiler is
fed only from spec fields the lesson also states in prose, and the long
description is written as a sentence-level restatement of the graph.

The second was scope. The production CourseJesus stack spans RAG, an agent
service, generated media, and a trained model, and most of it cannot run
deterministically or license-cleanly for a demo. AccessBridge deliberately takes
the one path that works offline and proves it end to end.

## What we learned

A deterministic renderer is a strong accessibility ally. When the picture is
generated from structured data, the text equivalent can be generated from the
same data, so tests can detect selected inconsistencies. The offline pack is built from the same validated lesson data. Prose/diagram agreement is checked by tests and still needs educator review.

## What comes next

- Educator review of the three lessons and the quiz rationales.
- A stronger layout pass for graphs with many nodes, plus a compact mode for
  narrow screens.
- Wiring the same pipeline into the CourseJesus lesson API so real courses can
  ship accessible packs, with the same rights checks.
- A learner study that measures whether the offline pack actually helps
  retention, which this build does not claim.

## Built with

Python 3.11, pydantic, deterministic SVG generation, Playwright and axe-core for
verification, and hand-written HTML, CSS, and JavaScript with no frontend
framework and no bundled web fonts.

## Try it

```powershell
.\scripts\start.ps1
```

Then open <http://127.0.0.1:15273/>. To see the offline pack, open
`app\dist\offline\stack-queue.html` directly from disk with the network off.

## Honest limits

This is an isolated competition build. It does not call the production
CourseJesus RAG, agent, image generation, or model services, and it does not
read or write learner scores or the `LEARNED` authority. The app has no accounts
and stores nothing about a learner. Practice results stay in page memory.

Public static demo: https://coursejesus-accessbridge.netlify.app/ . Final Devpost submission remains NOT_SUBMITTED and requires the owner’s personal declarations.


## Intended learner and a concrete before/after

The intended learner is a university student studying computing concepts in a
second language with intermittent connectivity. Previously they need to retain
a whole explanation and a diagram together. Here they can switch to Chinese,
read one short step, inspect equivalent text and source, practise three checks,
then save the complete HTML lesson for a disconnected commute. This is a
demonstrated interaction, not a measured improvement in retention.

## Reuse, event work and AI assistance

Pre-existing CourseJesus files at 1074b61: VisualSpec model, SVG validator and
original compiler (the latter retained for comparison). The offline helper came
from the owner-provided handoff. Event contributions include the standalone
bilingual app, accessible compiler/router, original lessons, algorithm checks,
offline integration, browser verification and packaging. This is an extension
of existing CourseJesus work, not a claim to have invented the whole product
during the event. Codex/ChatGPT assisted implementation, teaching-text drafting,
translation, tests, documentation and demo scripting. No runtime AI is used.
Pydantic and Python handle validation/builds; Playwright and axe-core are
test-only third parties. Rights retained with explicit judging-use permission;
third-party licenses remain intact. Eligibility is owner-confirmed, not assumed.
