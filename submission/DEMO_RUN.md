# Run the public demo

## Online

Open <https://coursejesus-accessbridge.netlify.app/>. The page is public and
does not require an account or API server.

## From the demo package

Requirements: Node.js 24.14.0 or newer.

```powershell
cd CourseJesus_AccessBridge_Demo
$env:COURSEMATE_API_PROXY = "http://127.0.0.1:15274"
node .\scripts\serve_web_dist.mjs .\frontend-dist 15273
```

Open <http://127.0.0.1:15273/accessbridge.html>. The API proxy is not contacted
by this static judging page.

Stop the server with `Ctrl+C`.

## Full source

The source ZIP contains the complete CourseJesus competition copy and README
instructions for the local guest shell, FastAPI boundary, tests, and deterministic
providers. It does not include credentials, production databases, uploads,
private learner data, model weights, or private media.

The source copy does not claim an owner representative-course E2E, public
full-stack hosting, live model generation, or final Devpost submission.
