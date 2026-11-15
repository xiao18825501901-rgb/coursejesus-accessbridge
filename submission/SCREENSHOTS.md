# Screenshot evidence

All files are under `evidence/screenshots/` unless a path is stated.

## Recommended Devpost order

1. `live-public-accessbridge.png` — anonymous public judging entry at
   <https://coursejesus-accessbridge.netlify.app/>.
2. `complete-site-guest-desktop.png` — anonymous guest view inside the complete
   CourseJesus shell. It shows the public course and omits management controls.
3. `complete-site-accessbridge-desktop.png` — AccessBridge lesson inside the
   complete shell. It shows bilingual navigation, large-text control, source
   disclosure, deterministic visual, and practice.
4. `complete-site-accessbridge-mobile-390.png` — mobile layout at 390 CSS pixels.
5. `complete-site-accessbridge-zoom200-reflow.png` — 640 CSS-pixel equivalent
   200% reflow check.
6. `AccessBridge_matrix-transform_en.html` — downloaded offline practice file;
   open it locally with network disabled to inspect the self-contained exercise.

## Full local evidence set

- `complete-site-guest-desktop.png`
- `complete-site-guest-mobile-360.png`
- `complete-site-guest-mobile-390.png`
- `complete-site-guest-tablet.png`
- `complete-site-guest-zoom200-reflow.png`
- `complete-site-accessbridge-desktop.png`
- `complete-site-accessbridge-mobile-390.png`
- `complete-site-accessbridge-zoom200-reflow.png`
- `public-accessbridge-entry-desktop.png`
- `public-accessbridge-entry-mobile-390.png`
- `live-public-accessbridge.png`
- `AccessBridge_matrix-transform_en.html`
- `final-video-frame-20s.png`
- `final-video-frame-100s.png`

Screenshots were rendered in installed Google Chrome against the isolated
production build and FastAPI UI extension. Axe reported zero WCAG A/AA
violations on the tested pages, but this is not a full WCAG certification.

The screenshots do not show the owner-created representative course, a live
Qwen/ComfyUI generation job, or a deployed public full-stack API because those
remain unverified. `live-public-accessbridge.png` is evidence for the
API-independent static judging entry only.

The final captioned video is `evidence/demo-captioned.mp4` (137.88 seconds,
1440×900 H.264). Captions are also provided separately in
`evidence/demo-captions.srt`.

