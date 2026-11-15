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

Required configuration:

- A new competition-only project.
- Independent database, uploads, cache, and logs.
- `WEB_ORIGIN` set to the competition frontend.
- `GUEST_SESSION_SECRET` generated for that deployment.
- Deterministic/mock providers for the safe demo.
- No production secrets or private course files.

Status: `BLOCKED_ACCOUNT`.

## 3. Publish the competition GitHub source

The source is ready for a clean competition repository or release artifact with
rights retained. If account-side repository creation or authentication is not
already available, create a public repository named
`coursejesus-accessed-hacks-2026`, then provide the clone/push URL.

Do not rewrite or force-push existing CourseJesus history. Do not publish
`.env`, credentials, student data, private media, model weights, runtime data, or
`review-inputs/`.

Status: `OWNER_ACCOUNT_ACTION` unless an existing authenticated session becomes
available.

## 4. Devpost identity and final submit

Re-open the current official AccessED Hacks overview and rules, confirm the
deadline, eligibility, team declaration, and required licenses, then complete
the account-specific fields. Do not substitute an OSI license for owner code and
do not claim unverified live generation or learning results.

The final Submit action and identity/terms declaration remain with the owner.

Status: `NOT_SUBMITTED`.

## 5. Exact temporary-directory cleanup

The requested cleanup target is:

`E:\Hackathon-2026\coursejesus-accessbridge\temporary-delivery\AccessBridge_Submission_20261113_153729`

The path was verified as an ordinary directory inside the allowed parent and not
a reparse point. The process policy rejected its recursive deletion twice. The
directory remains; delete only that exact folder after verification, or grant a
policy-compatible cleanup path.

Status: `BLOCKED_POLICY`.

