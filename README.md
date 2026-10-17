# Bugling Bulls • Broncos Intelligence Center v0.2 — Friends & Family Beta

A **read-only Broncos scouting dashboard** that fans can open from a link.
The first shared version focuses on *evidence-backed NFL play-by-play*, Denver
personnel/formation comparisons where charting is released, offensive and
defensive analysis, Bo Nix NGS trends and downloadable game reports.

**Important:** This is usable code, not a hosted URL yet. To publish it, you
must add these files to your GitHub repository and deploy via Streamlit. The
first full live-data import was **not** validated in the build environment.

## Quick local start — Windows

1. Extract this ZIP to a new folder, keeping the existing v0.1 folder untouched.
2. In VS Code choose **File → Open Folder** and select the extracted **v0.2** folder.
3. Open **Terminal → New Terminal**, then paste:

```powershell
powershell -ExecutionPolicy Bypass -File .\START_BRONCOS.ps1
```

4. Open http://localhost:8504 . On first launch it installs required Python
   libraries and downloads the real Denver play data.
5. To update a later game, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\REFRESH_DATA.ps1
```

The launch commands work in any folder location **as long as your terminal is
inside the folder containing `START_BRONCOS.ps1`**.

## Create a shareable website (after local validation)

### 1. Create a GitHub repository

- Sign in to https://github.com and create a repository, e.g.
  `bugling-bulls-broncos`.
- For a straightforward Streamlit Community Cloud fan beta, choose **Public**.
  A public GitHub repository means the **code and committed data are public**.
- Import the v0.2 app files from your local project into the repository. Avoid
  committing `.venv`, `data/scout_notes.csv`, `.streamlit/secrets.toml`, or any
  private notes / paid articles. `.gitignore` includes protective rules.
- Include the **hidden** `.github/workflows/` and `.streamlit/` directories.

If you have Git installed, the commands inside the v0.2 folder are:

```powershell
git init
git add .
git commit -m "Launch Bugling Bulls Broncos fan beta"
git branch -M main
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/bugling-bulls-broncos.git
git push -u origin main
```

Replace `YOUR_GITHUB_USERNAME` with your actual GitHub login. The above assumes
an **empty** newly created repository and working Git authentication. If your
repository has an existing README or commits, use GitHub Desktop to publish
this folder instead of running these commands blindly.

### 2. Create a published data snapshot

- From the GitHub repository, select **Actions → Refresh public Broncos data →
  Run workflow → Run workflow**.
- The action downloads available 2024–2026 plays, saves the public CSV/JSON
  files, runs tests and commits changed data to the repository.
- Review **Actions** for successful completion and confirm
  `data/broncos_plays.csv` is visible in the repo. If it fails, the app
  does not fake data: fix the error before sharing.
- Four daily checks are configured, but GitHub scheduling is approximate and
  upstream data feeds have varying publication delays. No immediate postgame
  SLA is implied. The workflow does not run just because fans visit the site.

### 3. Deploy to Streamlit Community Cloud

- Sign in to https://share.streamlit.io using GitHub.
- Choose **Create app → Yup, I have an app**.
- Select your `bugling-bulls-broncos` repository, branch `main`, and entry file
  `app.py`. Keep the root `requirements.txt`.
- Pick a shareable app URL if available and click **Deploy**.
- Open the generated `*.streamlit.app` website and share that URL with friends.

Official deployment guide:
https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy

### 4. Future updates

- Push changes to GitHub; Streamlit will redeploy automatically.
- Run the **Refresh public Broncos data** action for an immediate manual refresh
  attempt, or leave the scheduled checks enabled.
- Local scouting notes from v0.1 are **not** uploaded. The v0.2 app has no
  edit/save controls, logins, external data downloads or user-written files.

## What the viewer offers

1. **Weekly Intelligence**: Denver offensive/defensive scorecards, prior-three-
   game descriptive movement alerts, 2024–26 trends and game report download.
2. **Ask Bugling Bulls**: seven predefined, reproducible football questions;
   every answer includes supporting plays and transparent metric definitions.
3. **Personnel & Formations**: 11/12 etc., offense vs defense packages and
   formations where charting data is provided; never invents missing groupings.
4. **Offense / Defense**: play-call selection, pressure/rush count, distance,
   historical coach-period comparisons.
5. **Bo Nix NGS**: public player/week Next Gen Stats.
6. **Play Evidence**: search, filter, and CSV export of every supporting play.
7. **Data Quality**: source coverage, provenance, limitations and licenses.

## Known limitations

- Current-season detailed personnel, receiver formations, coverage families,
  offensive blocking scheme and defensive front are **not** independently
  derived from play descriptions. FTN participation is released post-season.
- Non-logged penalties and non-scrimmage plays are outside the sample. EPA is
  possession-team EPA; therefore lower defensive EPA allowed is good.
- Comparison groups may differ in opponent, down, distance and game script.
  Calculations are **descriptive**, not causal estimates, scouting-grade film
  conclusions or statistically powered forecasts.
- Questions are preprogrammed, **not** unrestricted natural-language AI.
- No live fan note submissions, account logins, video scraping, paid-film
  integration, or automatic expert-source assessment in v0.2.
- Scheduler may stop after prolonged GitHub repository inactivity; check the
  GitHub Actions tab periodically.

## File guide

| File | Purpose |
|---|---|
| `app.py` | Read-only Streamlit fan interface |
| `analysis_engine.py` | Tested metric definitions and trend flags |
| `data_pipeline.py` | Data downloads, joins, preservation and safe writes |
| `START_BRONCOS.ps1`, `REFRESH_DATA.ps1` | Windows local use |
| `.github/workflows/refresh-data.yml` | Scheduled updates to public data |
| `.github/workflows/validate.yml` | GitHub test suite |
| `.streamlit/config.toml` | Streamlit site theme |
| `DATA_LICENSES.md` | Source credit / license considerations |
| `tests/` | Offline tests with tiny synthetic test fixtures (never fan data) |

## Verify calculations locally

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

For substantive code changes, replace whole files rather than editing small
Python syntax fragments. Keep this as a separate project from the existing NFL
Outcome Prediction Model until its research backtests are validated.
