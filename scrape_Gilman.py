# CONVERTED GILMAN WITH ELIS TZ
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import pytz

def scrape_Gilman() -> pd.DataFrame:
    url = "https://app.showslinger.com/e1/460/924-gilman"
    soup = BeautifulSoup(requests.get(url).text, "html.parser")
    pt = pytz.timezone("US/Pacific")

    events: list[dict] = []
    for card in soup.select(".widget-grid"):
        # ----- scrape raw fields -----------------------------------------
        title_tag = card.select_one(".widget-name")
        date_tag  = card.select_one(".widget-time")
        link_tag  = card.select_one("a.btn-widget")
        img_tag   = card.select_one(".grid-img")

        title     = title_tag.get_text(strip=True) if title_tag else None
        date_text = date_tag.get_text(strip=True) if date_tag else None
        event_url = f"https://app.showslinger.com{link_tag['href']}" if link_tag else None
        image_url = img_tag["src"] if img_tag else None

        # ----- parse date/time -------------------------------------------
        start_dt = end_dt = start_time = end_time = None
        if date_text:
            try:
                # e.g. “Thu, May 30, 7:30 PM – …”
                _, date_str, time_str = date_text.split(", ")
                start_naive = datetime.strptime(f"{date_str} 2025 {time_str}",
                                                "%b %d %Y %I:%M %p")
                start_dt = pt.localize(start_naive)
                end_dt = start_dt + timedelta(hours=3)
                start_time = start_dt.strftime("%-I:%M %p")  # Use %#I on Windows
                end_time = end_dt.strftime("%-I:%M %p")
            except Exception:
                pass

        # ----- split bands -----------------------------------------------
        bands = [b.strip() for b in title.split(",")] if title else []
        headliner = bands[0] if len(bands) > 0 else None
        supporting_1 = bands[1] if len(bands) > 1 else None
        supporting_2 = bands[2] if len(bands) > 2 else None
        supporting_3 = bands[3] if len(bands) > 3 else None

        events.append({
            "Venue":             "924 Gilman",
            "Date":              start_dt.strftime("%a, %B %d") if start_dt else None,
            "Start Time":        start_time,
            "End Time":          end_time,
            "Start DateTime":    start_dt,
            "End DateTime":      end_dt,
            "Title":             title,
            "Image URL":         image_url,
            "Event URL":         event_url,
            "Headliner":         headliner,
            "Supporting Band 1": supporting_1,
            "Supporting Band 2": supporting_2,
            "Supporting Band 3": supporting_3,
        })

    cols = ["Venue", "Date", "Start Time", "End Time",
            "Start DateTime", "End DateTime", "Title", "Image URL",
            "Event URL", "Headliner", "Supporting Band 1",
            "Supporting Band 2", "Supporting Band 3"]

    return pd.DataFrame(events)[cols]

