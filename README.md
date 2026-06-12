# ME Trainee/Internship Tracker — Islamabad & Rawalpindi

A self-updating dashboard that checks a curated list of companies (defense
& heavy engineering, cement/energy, engineering consultancies, private
firms, and multinationals) for mechanical engineering trainee/internship
postings, plus gives you always-fresh LinkedIn and Indeed search links for
each one.

It runs entirely for free using GitHub Actions (the scheduled checker) and
GitHub Pages (the dashboard you view in your browser). Once set up, it
needs no maintenance — it checks every company once a day and updates the
page automatically.

---

## How it works

1. `scraper/companies.json` — the list of companies and their careers page
   URLs. Add, remove, or edit entries here at any time.
2. `scraper/scrape.py` — visits each company's careers page, looks for
   postings that mention mechanical engineering + trainee/internship/
   graduate/apprentice keywords, and also builds direct LinkedIn/Indeed
   search links for that company.
3. `.github/workflows/update-data.yml` — a GitHub Actions workflow that runs
   the script once a day (and any time you trigger it manually) and commits
   the results to `docs/data.json`.
4. `docs/index.html` — a dashboard page that reads `docs/data.json` and
   displays everything, grouped by category, with filters.

---

## One-time setup (about 10 minutes)

### 1. Create a free GitHub account
If you don't have one already: go to https://github.com/join and sign up.

### 2. Create a new repository
- Click the **+** icon (top right) → **New repository**
- Name it something like `me-job-tracker`
- Set it to **Public** (required for free GitHub Pages)
- Don't add a README/gitignore (we already have files) — just click **Create repository**

### 3. Upload these files
On the new repo's page, click **uploading an existing file** and drag in
this entire project folder (keeping the folder structure: `scraper/`,
`docs/`, `.github/workflows/`).

> Tip: if drag-and-drop of folders doesn't work in the browser, you can
> instead use GitHub Desktop (a free app) or `git` from a terminal to push
> the folder — but the web upload usually works fine for a small project
> like this.

### 4. Enable GitHub Pages
- Go to **Settings** (top of repo) → **Pages** (left sidebar)
- Under "Build and deployment" → "Source", choose **Deploy from a branch**
- Branch: `main`, Folder: `/docs` → **Save**
- After a minute or two, GitHub will show you a URL like
  `https://yourusername.github.io/me-job-tracker/` — that's your dashboard.

### 5. Enable and run the workflow
- Go to the **Actions** tab → you should see "Update job data"
- Click it, then click **Run workflow** (top right) to run it for the first
  time manually
- Wait ~1-2 minutes, then refresh your dashboard URL — it should now show
  results

After this, the workflow runs automatically every day at 05:00 UTC
(~10:00 AM Pakistan time). You don't need to do anything else.

---

## Customizing

### Add or fix a company
Open `scraper/companies.json` and add an entry like:

```json
{
  "name": "Some Company",
  "category": "Private Engineering & Manufacturing Firms",
  "careers_url": "https://example.com/careers",
  "fallback_url": "https://example.com/"
}
```

`fallback_url` is used if `careers_url` doesn't load — the scraper will try
to find a careers/jobs link on the homepage automatically.

### Adjust keywords
In `scraper/scrape.py`, edit `MECH_KEYWORDS` and `ENTRY_KEYWORDS` to broaden
or narrow what counts as a match (e.g. add "GTP", "design intern", etc.)

### Change the schedule
Edit the `cron` line in `.github/workflows/update-data.yml`. Cron times are
in UTC. For example `'0 14 * * *'` runs once a day at 2 PM UTC (7 PM PKT).

---

## Known limitations (important — read this)

- **Many company websites are JavaScript-heavy** (React/Vue single-page
  apps). The scraper uses simple HTML fetching, so it can't "see" content
  that's loaded dynamically by JavaScript. For these sites, the dashboard
  will show "Careers page not found" or "Checked — no current match" even
  if jobs exist — but it will still give you a direct link to the careers
  page and to LinkedIn/Indeed searches so you can check manually.
- **Some government sites (e.g. defense organizations) block automated
  access via `robots.txt`** or post jobs as scanned PDF images in
  newspapers rather than structured web pages. These are hard to automate
  reliably; treat the provided links as a starting point for manual checks.
- **Several `careers_url` values in `companies.json` are best-guesses** —
  some may 404 or redirect. After the first run, check the dashboard: any
  company marked "Site unreachable" or "Careers page not found" likely
  needs its URL corrected. Over the first few runs you'll likely want to
  fix a handful of these — treat it as a living config file you improve
  over time.
- **LinkedIn/Indeed are not scraped directly** — instead, the dashboard
  gives you direct search-result links scoped to each company + location +
  "mechanical engineer intern/trainee", which you can open with one click
  and will always show current results.

---

## Future improvements (optional, if you want to extend this later)

- Add a headless browser (e.g. Playwright) to the scraper to handle
  JavaScript-rendered career pages — this would significantly improve
  detection accuracy on modern company sites, at the cost of slower runs.
- Add email notifications (e.g. via a free service like SendGrid) when new
  postings are detected, comparing against the previous day's `data.json`.
- Add OCR for PDF job ads (common for government organizations like HIT,
  POF, PAC).
