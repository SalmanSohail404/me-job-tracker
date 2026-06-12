"""
ME Job Tracker - Scraper

Checks each company's careers page for mechanical engineering
trainee/internship postings, and also builds always-fresh search
links for LinkedIn and Indeed scoped to each company + location.

Output: docs/data.json  (consumed by the dashboard)
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, quote_plus

import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

# Some target sites have self-signed/misconfigured certs; we fall back to
# unverified requests for those, so silence the related warning.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ROOT = Path(__file__).resolve().parent.parent
COMPANIES_FILE = ROOT / "scraper" / "companies.json"
OUTPUT_FILE = ROOT / "docs" / "data.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}

REQUEST_TIMEOUT = 25


def _build_session():
    session = requests.Session()
    retries = Retry(
        total=2,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(HEADERS)
    return session


SESSION = _build_session()

# Keywords that indicate a mechanical-engineering-relevant posting
MECH_KEYWORDS = [
    "mechanical", "mech eng", "m.e.", "design engineer", "production engineer",
    "maintenance engineer", "manufacturing engineer", "hvac", "mep",
]

# Keywords that indicate an entry-level / trainee / internship posting
ENTRY_KEYWORDS = [
    "intern", "internship", "trainee", "graduate", "apprentice",
    "entry level", "fresh", "management trainee", "gtp",
    "junior", "mto", "management trainee officer",
]


def find_career_links(base_url, html):
    """Look for links on a homepage that likely lead to a careers/jobs page."""
    soup = BeautifulSoup(html, "html.parser")
    candidates = []
    for a in soup.find_all("a", href=True):
        text = (a.get_text() or "").strip().lower()
        href = a["href"]
        if any(k in text for k in ["career", "job", "vacanc", "internship", "join us", "recruitment"]) or \
           any(k in href.lower() for k in ["career", "job", "vacanc", "recruit"]):
            candidates.append(urljoin(base_url, href))
    seen = set()
    out = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def fetch(url):
    for verify in (True, False):
        try:
            resp = SESSION.get(
                url, timeout=REQUEST_TIMEOUT, allow_redirects=True, verify=verify
            )
            if resp.status_code == 200 and resp.text:
                return resp.text
            # Some servers return non-200 on HEAD-like checks but still
            # serve real content on GET with a trailing slash.
            if resp.status_code in (403, 404) and not url.endswith("/"):
                resp2 = SESSION.get(
                    url + "/", timeout=REQUEST_TIMEOUT, allow_redirects=True,
                    verify=verify,
                )
                if resp2.status_code == 200 and resp2.text:
                    return resp2.text
        except requests.exceptions.SSLError:
            continue  # retry with verify=False
        except requests.RequestException:
            return None
    return None


def extract_postings(base_url, html):
    """Extract candidate job postings (text + link) that match our keywords."""
    soup = BeautifulSoup(html, "html.parser")
    matches = []

    for a in soup.find_all("a", href=True):
        text = (a.get_text() or "").strip()
        if not text or len(text) < 4:
            continue
        lower = text.lower()
        if any(k in lower for k in MECH_KEYWORDS) and any(k in lower for k in ENTRY_KEYWORDS):
            matches.append({"title": text, "link": urljoin(base_url, a["href"])})
        elif any(k in lower for k in ENTRY_KEYWORDS) and "engineer" in lower:
            matches.append({"title": text, "link": urljoin(base_url, a["href"])})

    full_text = soup.get_text(separator="\n")
    for line in full_text.splitlines():
        line = line.strip()
        if len(line) < 8 or len(line) > 200:
            continue
        lower = line.lower()
        if any(k in lower for k in MECH_KEYWORDS) and any(k in lower for k in ENTRY_KEYWORDS):
            matches.append({"title": line, "link": base_url})

    seen_titles = set()
    deduped = []
    for m in matches:
        key = m["title"].lower()
        if key not in seen_titles:
            seen_titles.add(key)
            deduped.append(m)
    return deduped[:15]


def build_external_search_links(company_name):
    """Build always-fresh LinkedIn and Indeed search links for this company."""
    linkedin = (
        "https://www.linkedin.com/jobs/search/?keywords="
        + quote_plus(f"{company_name} mechanical engineer")
        + "&location=" + quote_plus("Islamabad, Pakistan")
    )
    indeed = (
        "https://pk.indeed.com/jobs?q="
        + quote_plus(f"{company_name} mechanical engineer intern")
        + "&l=" + quote_plus("Islamabad")
    )
    return {"linkedin": linkedin, "indeed": indeed}


def check_company(company):
    name = company["name"]
    careers_url = company["careers_url"]
    fallback_url = company.get("fallback_url")

    result = {
        "name": name,
        "category": company.get("category", "Other"),
        "checked_url": careers_url,
        "status": "unreachable",
        "postings": [],
        "external_search": build_external_search_links(name),
    }

    html = fetch(careers_url)
    used_url = careers_url

    if html is None and fallback_url:
        home_html = fetch(fallback_url)
        if home_html:
            links = find_career_links(fallback_url, home_html)
            for link in links:
                html = fetch(link)
                if html:
                    used_url = link
                    break
            if html is None:
                result["status"] = "homepage_only"
                result["checked_url"] = fallback_url
                return result

    if html is None:
        return result

    result["checked_url"] = used_url
    result["status"] = "checked"
    result["postings"] = extract_postings(used_url, html)
    if result["postings"]:
        result["status"] = "matches_found"

    return result


def main():
    companies = json.loads(COMPANIES_FILE.read_text())
    results = []

    for company in companies:
        print(f"Checking: {company['name']} ...")
        try:
            results.append(check_company(company))
        except Exception as e:
            results.append({
                "name": company["name"],
                "category": company.get("category", "Other"),
                "checked_url": company["careers_url"],
                "status": "error",
                "postings": [],
                "external_search": build_external_search_links(company["name"]),
                "error": str(e),
            })
        time.sleep(1)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "companies": results,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"Wrote {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
