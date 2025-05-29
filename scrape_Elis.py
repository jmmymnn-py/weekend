"""
scrape_Elis.py  ―  Eli’s Mile-High Club event scraper
Compatible with Python 3.8 / 3.9  (no PEP 604 “X | Y” types)  
Returns a tidy pandas DataFrame with start / end datetimes converted to US-Pacific.
"""

from __future__ import annotations   # forward-refs allowed in type hints (<3.10)

import json
from typing import Optional, List, Dict, Any

from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import pytz
import requests


def scrape_Elis() -> pd.DataFrame:
    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def find_events_node(obj: Any) -> Optional[List[Dict[str, Any]]]:
        """
        Recursively walk the warm-up JSON blob until we hit the list that
        contains the actual event dictionaries (they all have a 'title').
        """
        if isinstance(obj, dict):
            for k, v in obj.items():
                if (
                    k == "events"
                    and isinstance(v, list)
                    and all(isinstance(i, dict) and "title" in i for i in v)
                ):
                    return v
                nested = find_events_node(v)
                if nested:
                    return nested
        elif isinstance(obj, list):
            for item in obj:
                nested = find_events_node(item)
                if nested:
                    return nested
        return None

    def iso_to_pt(iso: Optional[str]) -> Optional[datetime]:
        """
        Convert an ISO-8601 string (which Wix gives in Zulu time) to an
        aware datetime in US/Pacific. Returns None if parsing fails.
        """
        if not iso:
            return None
        try:
            dt_utc = datetime.fromisoformat(iso.replace("Z", "+00:00"))
            return dt_utc.astimezone(pt)
        except Exception:
            return None

    # ------------------------------------------------------------------ #
    # scrape warm-up JSON
    # ------------------------------------------------------------------ #
    url = "https://www.elismilehighclub.com/"
    soup = BeautifulSoup(requests.get(url, timeout=30).text, "html.parser")

    script_tag = soup.find("script", {"id": "wix-warmup-data"})
    if script_tag is None:
        raise RuntimeError("Could not locate warm-up JSON on Eli’s site")

    warmup_data = json.loads(script_tag.string)
    events = find_events_node(warmup_data)
    if events is None:
        raise RuntimeError("Warm-up JSON did not contain an 'events' list")

    # ------------------------------------------------------------------ #
    # normalise rows
    # ------------------------------------------------------------------ #
    pt = pytz.timezone("US/Pacific")
    rows: List[Dict[str, Any]] = []

    for event in events:
        raw_title = event.get("title", "")
        title_upper = raw_title.upper()

        # Strip the "BLUE MONDAYS - " prefix that appears on weekly residencies
        if "BLUE MONDAYS - " in title_upper:
            split_at = title_upper.index("BLUE MONDAYS - ") + len("BLUE MONDAYS - ")
            raw_title = raw_title[split_at:].strip()

        cfg = event.get("scheduling", {}).get("config", {})
        start_dt = iso_to_pt(cfg.get("startDate"))
        end_dt = iso_to_pt(cfg.get("endDate"))

        rows.append(
            {
                "Venue": "Eli's Mile High Club",
                "Date": start_dt.strftime("%a, %B %d") if start_dt else "",
                "Start Time": start_dt.strftime("%-I:%M %p") if start_dt else "",
                "End Time": end_dt.strftime("%-I:%M %p") if end_dt else "",
                "Start DateTime": start_dt,
                "End DateTime": end_dt,
                "Title": raw_title,
                "Image URL": event.get("mainImage", {}).get("url", ""),
                "Event URL": (
                    f"https://www.elismilehighclub.com/event-details/{event.get('slug')}"
                    if event.get("slug")
                    else ""
                ),
            }
        )

    # ------------------------------------------------------------------ #
    # explode Title into Headliner / Supporting Band columns
    # ------------------------------------------------------------------ #
    df = pd.DataFrame(rows)

    # split on " / "
    title_parts = df["Title"].str.split(" / ", expand=True)
    title_parts.columns = ["Headliner"] + [
        f"Supporting Band {i}" for i in range(1, len(title_parts.columns))
    ]

    return pd.concat([df, title_parts], axis=1)