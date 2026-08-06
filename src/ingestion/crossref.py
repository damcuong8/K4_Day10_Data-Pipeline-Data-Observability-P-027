import dataclasses
from dataclasses import dataclass
import hashlib
import html
import json
import logging
from pathlib import Path
import re
import time
from typing import Any

import requests

from core.config import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _clean_abstract(raw_abstract: str | None) -> str:
    """Clean HTML/XML tags, unescape entities, and strip whitespace from abstract."""
    if not raw_abstract:
        return ""
    # Strip XML/HTML tags (e.g. <jats:p>, <jats:title>, etc.)
    text = re.sub(r"<[^>]+>", "", raw_abstract)
    # Unescape HTML entities (&amp;, &lt;, &gt;, etc.)
    text = html.unescape(text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_date(date_obj: dict[str, Any] | None) -> str:
    """Extract ISO date YYYY-MM-DD from Crossref date-parts structure."""
    if not date_obj or not isinstance(date_obj, dict):
        return ""
    date_parts = date_obj.get("date-parts", [])
    if not date_parts or not isinstance(date_parts, list) or not date_parts[0]:
        return ""
    parts = date_parts[0]
    try:
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 1
        day = int(parts[2]) if len(parts) > 2 else 1
        return f"{year:04d}-{month:02d}-{day:02d}"
    except (ValueError, TypeError, IndexError):
        return ""


def _extract_authors(author_list: list[dict[str, Any]] | None) -> list[str]:
    """Format author list into list of string names."""
    if not author_list or not isinstance(author_list, list):
        return []
    authors = []
    for a in author_list:
        if not isinstance(a, dict):
            continue
        given = a.get("given", "").strip()
        family = a.get("family", "").strip()
        name = a.get("name", "").strip()
        if given and family:
            authors.append(f"{given} {family}")
        elif family:
            authors.append(family)
        elif given:
            authors.append(given)
        elif name:
            authors.append(name)
    return authors


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref API payload into a list of PaperRecord.

    1. Iterates over `payload["message"]["items"]`.
    2. Extracts DOI/stable paper_id, title, summary, authors, subject/categories, dates, URLs.
    3. Normalizes text and filters invalid records (missing title).
    4. Returns list of `PaperRecord`.
    """
    message = payload.get("message", payload)
    if isinstance(message, dict):
        items = message.get("items", [])
    elif isinstance(payload, list):
        items = payload
    else:
        items = []

    records: list[PaperRecord] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        # Extract title
        title_list = item.get("title", [])
        if isinstance(title_list, list) and title_list:
            raw_title = title_list[0]
        elif isinstance(title_list, str):
            raw_title = title_list
        else:
            raw_title = ""

        title = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", str(raw_title)))).strip()
        if not title:
            # Skip invalid record without title
            continue

        # Paper ID: Prefer DOI, fallback to item id or hash of title
        doi = item.get("DOI", "").strip()
        if doi:
            paper_id = doi
        else:
            item_id = str(item.get("id", "")).strip()
            if item_id:
                paper_id = item_id
            else:
                paper_id = f"crossref-{hashlib.md5(title.encode('utf-8')).hexdigest()[:12]}"

        # Summary / Abstract
        summary = _clean_abstract(item.get("abstract", ""))

        # Authors
        authors = _extract_authors(item.get("author", []))

        # Subject / Categories
        raw_subjects = item.get("subject", [])
        categories = [str(s).strip() for s in raw_subjects if str(s).strip()] if isinstance(raw_subjects, list) else []
        primary_category = categories[0] if categories else ""

        # Dates: published-online / published-print / issued / created
        pub_date = (
            _parse_date(item.get("published-online"))
            or _parse_date(item.get("published-print"))
            or _parse_date(item.get("issued"))
            or _parse_date(item.get("created"))
        )
        updated_date = (
            _parse_date(item.get("deposited"))
            or _parse_date(item.get("indexed"))
            or pub_date
        )

        # URLs
        abs_url = item.get("URL", "").strip()
        pdf_url = ""
        links = item.get("link", [])
        if isinstance(links, list):
            for link in links:
                if isinstance(link, dict) and link.get("content-type") == "application/pdf":
                    pdf_url = link.get("URL", "").strip()
                    break

        # Comment / Journal name
        container_titles = item.get("container-title", [])
        comment = container_titles[0].strip() if isinstance(container_titles, list) and container_titles else item.get("publisher", "")
        if not isinstance(comment, str):
            comment = str(comment)

        record = PaperRecord(
            paper_id=paper_id,
            title=title,
            summary=summary,
            authors=authors,
            categories=categories,
            primary_category=primary_category,
            published=pub_date,
            updated=updated_date,
            abs_url=abs_url,
            pdf_url=pdf_url,
            comment=comment,
        )
        records.append(record)

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch raw records from Crossref API or load cached raw records snapshot.

    1. Checks if cached raw_records_json exists when refresh_source is False.
    2. Constructs query params and headers with polite User-Agent.
    3. Calls API with exponential backoff retry for HTTP 429/503.
    4. Saves raw API payload to settings.paths.raw_api_response.
    5. Parses payload with parse_crossref_payload.
    6. Saves parsed records to settings.paths.raw_records_json.
    """
    raw_records_path = settings.paths.raw_records_json
    raw_api_path = settings.paths.raw_api_response

    # Check cache first if refresh_source is False
    if not settings.refresh_source and raw_records_path.exists():
        try:
            logger.info("Loading cached raw records from %s", raw_records_path)
            return load_raw_records(raw_records_path)
        except Exception as err:
            logger.warning("Failed to load cached raw records (%s). Re-fetching from source API...", err)

    url = "https://api.crossref.org/works"
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    headers = {
        "User-Agent": "DataPipelineLab/1.0 (mailto:student@lab.local; Python/crossref.py)",
    }

    max_retries = 5
    backoff_factor = 2.0
    payload: dict[str, Any] = {}

    for attempt in range(max_retries):
        try:
            logger.info("Fetching Crossref API (attempt %d/%d)...", attempt + 1, max_retries)
            resp = requests.get(url, params=params, headers=headers, timeout=20)
            if resp.status_code == 200:
                payload = resp.json()
                break
            elif resp.status_code in (429, 502, 503, 504):
                sleep_time = backoff_factor ** attempt
                logger.warning("HTTP %d received. Retrying in %.1f seconds...", resp.status_code, sleep_time)
                time.sleep(sleep_time)
            else:
                resp.raise_for_status()
        except (requests.RequestException, ValueError) as err:
            if attempt == max_retries - 1:
                logger.error("Max retries exceeded when calling Crossref API: %s", err)
                raise
            sleep_time = backoff_factor ** attempt
            logger.warning("Request error (%s). Retrying in %.1f seconds...", err, sleep_time)
            time.sleep(sleep_time)

    # Save raw API response JSON
    raw_api_path.parent.mkdir(parents=True, exist_ok=True)
    with open(raw_api_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    logger.info("Saved raw API response to %s", raw_api_path)

    # Parse payload
    records = parse_crossref_payload(payload)

    # Save raw records JSON
    raw_records_path.parent.mkdir(parents=True, exist_ok=True)
    serialized_records = [dataclasses.asdict(r) for r in records]
    with open(raw_records_path, "w", encoding="utf-8") as f:
        json.dump(serialized_records, f, indent=2, ensure_ascii=False)
    logger.info("Saved %d parsed raw records to %s", len(records), raw_records_path)

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Read JSON snapshot and deserialize into a list of PaperRecord objects."""
    if not path.exists():
        raise FileNotFoundError(f"Raw records file not found at {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected list of records in {path}, got {type(data)}")

    records: list[PaperRecord] = []
    for item in data:
        if isinstance(item, dict):
            records.append(PaperRecord(**item))
    return records

