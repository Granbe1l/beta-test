# Publish and verify the real Streamlit demo

> Status: **not yet publicly verified**. Local browser screenshots and
> successful GitHub Actions tests do **not** establish that recruiters can
> open the Streamlit app. Do not add a fake URL to the portfolio.

## Preferred: Streamlit Community Cloud

The full application reads the checked-in data/github_public_snapshot.json.gz
file. No GitHub token, PostgreSQL server, or private secrets are required
to view the read-only dashboard.

1. Sign in with the repository-owner GitHub account at
   https://share.streamlit.io/.
2. Choose **Create app → Yup, I have an app**.
3. Enter **repository:** Granbe1l/beta-test.
4. Enter **branch:** main.
5. Enter **main file path:** streamlit_app.py.
6. Deploy, then make the app public if visibility controls are shown.
7. Copy the actual HTTPS URL ending in .streamlit.app; do not guess it.

Official guide:
https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app

The GitHub code contributor cannot authorize Streamlit hosting on behalf
of the repository owner. The owner must sign in to the hosting service.

## Mandatory P0-3 acceptance test

After the hosted app exists:

1. Open **GitHub Actions → Verify public Streamlit deployment → Run workflow**.
2. Paste the real public HTTPS URL into its app_url field.
3. The workflow must finish **successfully**. Download the resulting
   public-streamlit-verification screenshot artifact.
4. The check must confirm:
   - The URL is public and reachable without an authentication prompt.
   - The real Streamlit Dashboard and at least one Plotly chart render.
   - The on-page snapshot timestamp matches the checked-in GitHub snapshot.
   - The Key findings navigation loads and shows review information.
   - Screenshots of both actual hosted pages can be captured.
5. Open the same URL in a logged-out/private browser window to confirm
   that a recruiter does not need access to the owner's Streamlit account.

Only after all checks pass should the URL be added to README, the
portfolio website, or CV.

## Optional continuous checking after deployment

In GitHub repository Settings → Secrets and variables → Actions →
Variables, create a repository variable named PUBLIC_APP_URL containing
the actual full HTTPS URL. Subsequent successful collector workflows
then trigger the public-site check. With no URL variable set, that
automatic verification is skipped—not falsely marked as successful.

A snapshot publishing commit includes [skip ci], and hosted Streamlit
updates may take time to propagate. If freshness checking fails,
inspect Streamlit Cloud logs, verify the branch, reboot/reload if
necessary, then rerun the manual verification. A successful localhost
screenshot is not proof of a public demo.

## Important limits

This verifies a real public interface and the snapshot it renders.
It does not establish complete lifetime GitHub history, perfectly timed
four-hour updates, visitor broadband speed, or access to private SLAs and
client milestones. All activity statistics remain bounded observations.

## Alternative hosting

Services such as Render can host this Streamlit app but require a
separate hosting account. Do not invent or claim a connection. If
Streamlit Community Cloud cannot be used, choose and authorize one
hosting provider before attempting that alternative.
