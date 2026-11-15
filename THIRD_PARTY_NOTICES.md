# Third-party notices

This file summarizes direct third-party dependencies used by the competition
copy. The exact transitive graph is recorded in `package-lock.json`,
`pnpm-lock.yaml`, `services/openjev-service/package-lock.json`, and
`services/rag-api/requirements.txt`.

Installing dependencies does not transfer ownership. Each package keeps the
license shipped in its package metadata and license files.

## Frontend runtime dependencies

| Package | Version | License |
|---|---:|---|
| `@clerk/react` | 6.14.1 | MIT |
| `i18next` | 26.4.2 | MIT |
| `katex` | 0.19.1 | MIT |
| `react` | 19.2.8 | MIT |
| `react-dom` | 19.2.8 | MIT |
| `react-i18next` | 17.0.15 | MIT |
| `react-router-dom` | 7.18.2 | MIT |

## Agent API dependencies

| Package | Version | License |
|---|---:|---|
| `@clerk/express` | 2.1.55 | MIT |
| `ajv` | 8.20.0 | MIT |
| `cors` | 2.8.6 | MIT |
| `express` | 5.2.1 | MIT |
| `express-rate-limit` | 8.6.2 | MIT |
| `helmet` | 8.3.0 | MIT |
| `openai` | 7.4.0 | Apache-2.0 |

## Browser and build tooling

| Package | Version | License |
|---|---:|---|
| `@axe-core/playwright` | 4.10.2 | MPL-2.0 |
| `@playwright/test` | 1.62.1 | Apache-2.0 |
| `esbuild` | 0.28.1 | MIT |
| `jsdom` | 29.1.1 | MIT |
| `typescript` | 5.9.3 | Apache-2.0 |
| `vite` | 8.3.8 | MIT |
| `vitest` | 4.1.12 | MIT |

## Python runtime dependencies

| Package | Version | License |
|---|---:|---|
| `fastapi` | 0.141.1 | MIT |
| `httpx` | 0.28.1 | BSD-3-Clause |
| `alibabacloud-oss-v2` | 1.4.0 | Apache-2.0 |
| `alibabacloud-credentials` | 1.0.12 | Apache-2.0 |
| `clerk-backend-api` | 6.0.1 | MIT |
| `openai` | 2.53.0 | Apache-2.0 |
| `Pillow` | 12.3.0 | MIT-CMU |
| `pydantic-settings` | 2.15.0 | MIT |
| `pypdf` | 6.15.0 | BSD-3-Clause |
| `python-docx` | 1.2.0 | MIT |
| `python-multipart` | 0.0.32 | Apache-2.0 |
| `python-pptx` | 1.0.2 | MIT |
| `tzdata` | 2025.2 | Apache-2.0 |
| `uvicorn` | 0.52.1 | BSD-3-Clause |

## Vendored `open-jev`

`services/openjev-service/vendor/open-jev-0.1.2.tgz` is recorded by
`VENDOR_MANIFEST.json` as package `open-jev` version `0.1.2`, upstream
`https://github.com/nico-martin/open-jev`, under MIT. The frozen model and model
weights are not in this delivery.

## CourseJesus brand files

The images under `apps/web/public/brand/` and
`apps/web/brand-source/coursejesus-logo-source.png` are owner-authorized
CourseJesus product assets. They are not relicensed by this document.

