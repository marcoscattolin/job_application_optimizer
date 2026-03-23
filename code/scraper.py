"""
LinkedIn job posting scraper.

Fetches the job description from a public LinkedIn job URL.
Works with URLs of the form:
  https://www.linkedin.com/jobs/view/1234567890/
  https://www.linkedin.com/jobs/view/some-job-title-at-company-1234567890/
"""

from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup
from loguru import logger

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

_TIMEOUT = 15  # seconds


def _extract_job_id(url: str) -> str | None:
    """Extract numeric job ID from a LinkedIn jobs URL."""
    match = re.search(r"/jobs/view/(?:[^/]+-)?(\d+)", url)
    return match.group(1) if match else None


def fetch_linkedin_job(url: str) -> str:
    """
    Fetch job description text from a LinkedIn job posting URL.

    Returns plain text with title, company, location, and description.
    Raises ValueError if the page cannot be parsed or the content is blocked.
    """
    logger.debug(f"Fetching LinkedIn job from: {url}")

    # Normalise to canonical job URL if we have the ID
    job_id = _extract_job_id(url)
    fetch_url = f"https://www.linkedin.com/jobs/view/{job_id}/" if job_id else url
    logger.debug(f"Canonical URL: {fetch_url}")

    try:
        resp = requests.get(fetch_url, headers=_HEADERS, timeout=_TIMEOUT)
    except requests.RequestException as exc:
        raise ValueError(f"Network error fetching LinkedIn URL: {exc}") from exc

    if resp.status_code == 429:
        raise ValueError(
            "LinkedIn rate-limited this request (HTTP 429). "
            "Wait a few minutes and try again, or paste the job description into a file."
        )
    if resp.status_code != 200:
        raise ValueError(
            f"LinkedIn returned HTTP {resp.status_code}. "
            "The job may have been removed or the URL is incorrect."
        )

    soup = BeautifulSoup(resp.text, "html.parser")

    # --- job title ---
    title_el = (
        soup.select_one("h1.top-card-layout__title")
        or soup.select_one("h1.topcard__title")
        or soup.select_one("h1")
    )
    title = title_el.get_text(strip=True) if title_el else ""

    # --- company ---
    company_el = (
        soup.select_one("a.topcard__org-name-link")
        or soup.select_one(".topcard__org-name-link")
        or soup.select_one("a[data-tracking-control-name='public_jobs_topcard-org-name']")
        or soup.select_one(".top-card-layout__card .topcard__flavor--black-link")
    )
    company = company_el.get_text(strip=True) if company_el else ""

    # --- location ---
    location_el = (
        soup.select_one(".topcard__flavor--bullet")
        or soup.select_one(".top-card-layout__bullet")
    )
    location = location_el.get_text(strip=True) if location_el else ""

    # --- description body ---
    desc_el = (
        soup.select_one("div.show-more-less-html__markup")
        or soup.select_one("div.description__text")
        or soup.select_one("section.description")
    )

    if not desc_el:
        # LinkedIn may redirect to login wall
        if "authwall" in resp.url or "login" in resp.url:
            raise ValueError(
                "LinkedIn redirected to the login wall. "
                "Copy the job description manually into a text file and use --job instead."
            )
        raise ValueError(
            "Could not find the job description in the page. "
            "LinkedIn may have changed its HTML structure, or the job is no longer public."
        )

    description = desc_el.get_text(separator="\n", strip=True)

    parts: list[str] = []
    if title:
        parts.append(f"Job Title: {title}")
    if company:
        parts.append(f"Company: {company}")
    if location:
        parts.append(f"Location: {location}")
    if parts:
        parts.append("")  # blank line before body
    parts.append(description)

    result = "\n".join(parts)
    logger.info(
        f"Scraped LinkedIn job | title={title!r} | company={company!r} | chars={len(result)}"
    )
    return result
