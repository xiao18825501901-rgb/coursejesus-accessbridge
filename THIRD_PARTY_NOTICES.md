# Third-party notices

## Runtime dependencies

| Component | Version | License | Use here |
| --- | --- | --- | --- |
| Python | 3.11.9 | PSF License | Interpreter |
| pydantic | 2.14.3 | MIT | Lesson and VisualSpec schema validation |
| pydantic-core | 2.50.4 | MIT | pydantic dependency |
| typing-extensions | 4.16.0 | PSF-2.0 | pydantic dependency |
| annotated-types | 0.8.0 | MIT | pydantic dependency |
| typing-inspection | 0.4.5 | MIT | pydantic dependency |

The shipped application needs only the Python standard library plus `pydantic`.
The build and the server import nothing else.

## Test-only dependencies

| Component | Version | License | Use here |
| --- | --- | --- | --- |
| pytest | 9.2.0 | MIT | Test runner |
| playwright | 1.65.1 | Apache-2.0 | Browser automation for accessibility and offline checks |
| axe-core | 4.14.0 | MPL-2.0 | Accessibility scan, vendored at `tests/vendor/axe.min.js` |

The axe-core license text is reproduced at `tests/vendor/AXE_LICENSE.txt`.
axe-core is used only inside the test run; it is not shipped in `app/dist/` and
is not loaded by any generated page.

Playwright downloads a Chromium build for testing. That browser is not part of
this folder and is not redistributed here.

## Upstream CourseJesus files

Three files from `coursemate-ai@1074b61` are reproduced byte-for-byte in
`source-visual-1074/` and imported into `app/visual/`. Current owner permission is recorded in
`LICENSE_NOTES.md`; no historical upstream license is asserted. They are listed here so the provenance is
visible, not to assert a license for them.

## Fonts and media

No web font, icon set, stock photo, illustration, audio clip, or video is
bundled. Pages use the system font stack and inline SVG generated at build time.
The demo recording in `evidence/` is a screen capture of this app.
