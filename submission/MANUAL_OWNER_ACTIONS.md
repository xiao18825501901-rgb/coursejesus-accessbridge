# Owner-only actions

These items require the owner's content, identity, or a hosting account that
this isolated copy cannot safely supply.

## 1. Create the representative course

In the controlled CourseJesus environment, create one course and at least one
knowledge point that can be shown publicly. Enter the real content yourself and
provide the resulting course/knowledge-point identifiers to the competition
session.

Acceptance needed:

- Course appears in the public guest view.
- Knowledge-point tree renders.
- One image and one video are generated in the current run.
- A historical visual is visibly distinguished from the new generation.
- One practice question is answered and judged with source-grounded feedback.
- No private student, grade, profile, or admin data appears.

Status: `BLOCKED_OWNER`.

## 2. Provide a free full-stack hosting account

A static host cannot serve the FastAPI guest API. Publish the frontend and
guest-capable backend under a new name that does not target `coursejesus.com`.
Use free capacity already present on the account; do not purchase a paid plan
for this task.

The API-independent static judging entry is already public and verified at
<https://coursejesus-accessbridge.netlify.app/>. This action remains necessary
only for a public complete-shell and public FastAPI guest API.

Required configuration:

- A new competition-only project.
- Independent database, uploads, cache, and logs.
- `WEB_ORIGIN` set to the competition frontend.
- `GUEST_SESSION_SECRET` generated for that deployment.
- Deterministic/mock providers for the safe demo.
- No production secrets or private course files.

Status: `BLOCKED_ACCOUNT` for the full-stack environment; the static
AccessBridge entry is `VERIFIED_LIVE`.

## 3. Devpost identity and final submit

Re-open the current official AccessED Hacks overview and rules, confirm the
deadline, eligibility, team declaration, and required licenses, then complete
the account-specific fields. Do not substitute an OSI license for owner code and
do not claim unverified live generation or learning results.

The final Submit action and identity/terms declaration remain with the owner.

Status: `NOT_SUBMITTED`.

## 4. Exact temporary-directory cleanup

The requested cleanup target is:

`E:\Hackathon-2026\coursejesus-accessbridge\temporary-delivery\AccessBridge_Submission_20261113_153729`

The path was verified as an ordinary directory inside the allowed parent and not
a reparse point. The process policy rejected its recursive deletion twice. The
directory remains; delete only that exact folder after verification, or grant a
policy-compatible cleanup path.

Status: `BLOCKED_POLICY`.

