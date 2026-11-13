# Verified browser screenshot gallery

These files are compact previews of **actual Chrome/Playwright captures**
of Streamlit running against the committed public GitHub snapshot. They
are not screenshots of a publicly deployed Streamlit Community Cloud app.

The preview builder is `scripts/prepare_gallery.py`; it reads the images
and browser-audit JSON from `scripts/capture_ui.py`, refuses to publish
without a six-page mobile test, resizes originals without changing their
content, and writes `manifest.json` with SHA-256 of the original PNG,
capture UTC timestamp, source commit, and mobile page count.

**How publication works:** The UI screenshot GitHub Actions workflow tests
desktop and all six mobile pages. On successful runs triggered by relevant
UI/code changes on `main`, a separate job with limited
`contents: write` permission commits the seven small JPEG previews and
manifest. Pull-request screenshot jobs are strictly read-only; a snapshot
refresh alone does not trigger a new permanent-gallery commit. This avoids
inflating the Git history every six hours.

**Important caveats:** The previews are point-in-time images from the
commit in the manifest. Exact figures naturally change when new snapshots
are collected. The gallery does not demonstrate real HR participant
understanding, continuous six-hour scheduling, complete repository history,
or internet-accessible hosted deployment. The full-size PNGs and original
CSV exports remain in [GitHub Actions artifacts](https://github.com/Granbe1l/beta-test/actions/workflows/ui-screenshots.yml)
and may expire; these checked-in JPEG previews do not.

Before publishing the website in a CV, separately run the real-public-site
verification described in [the deployment guide](../PUBLIC_DEPLOYMENT.md).
