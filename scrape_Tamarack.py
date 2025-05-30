#scrape_Tamarack

import requests
import pandas as pd
from datetime import datetime
import pytz
import re

def scrape_Tamarack() -> pd.DataFrame:
    url = 'https://clients6.google.com/calendar/v3/calendars/01b5fe92358ed0aed1cbb5c52428696a32a32fa1da31b10f6b65ca5777845b00%40group.calendar.google.com/events'
    from datetime import datetime, time
    from dateutil.relativedelta import relativedelta

# Get today's date at midnight
    today_midnight = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
    three_months_later = today_midnight + relativedelta(months=3)
    params = {
        'calendarId': '01b5fe92358ed0aed1cbb5c52428696a32a32fa1da31b10f6b65ca5777845b00@group.calendar.google.com',
        'singleEvents': 'true',
        'eventTypes': ['default', 'focusTime', 'outOfOffice'],
        'timeZone': 'America/Los_Angeles',
        'maxAttendees': '1',
        'maxResults': '250',
        'sanitizeHtml': 'true',
        'timeMin': today_midnight.isoformat(),
        'timeMax': three_months_later.isoformat(),
        'key': 'AIzaSyDOtGM5jr8bNp1utVpG2_gSRH03RNGBkI8',
        '$unique': 'gc456'
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:138.0) Gecko/20100101 Firefox/138.0',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'X-JavaScript-User-Agent': 'google-api-javascript-client/1.1.0',
        'X-Requested-With': 'XMLHttpRequest',
        'X-Goog-Encode-Response-If-Executable': 'base64',
        'X-ClientDetails': 'appVersion=5.0 (Macintosh)&platform=MacIntel&userAgent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:138.0) Gecko/20100101 Firefox/138.0',
        'Origin': 'https://calendar.google.com',
        'Connection': 'keep-alive',
        'Referer': 'https://calendar.google.com/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'TE': 'trailers'
    }

    # Request and load JSON
    response = requests.get(url, headers=headers, params=params)
    print(response)
    data = response.json()
    events = data.get('items', [])
    df = pd.json_normalize(events)

    # Filter for events that contain 'show' in summary
    df_show = df[df['summary'].str.contains('show', case=False, na=False)]

    # Timezone and parser
    pt = pytz.timezone("US/Pacific")
    def to_pt(iso_str):
        try:
            return datetime.fromisoformat(iso_str).astimezone(pt)
        except Exception:
            return None

    rows = []
    for _, row in df_show.iterrows():
        start_iso = row.get("start.dateTime")
        end_iso = row.get("end.dateTime")
        raw_title = row.get("summary", "")
        html_link = row.get("htmlLink", "")
        start_dt = to_pt(start_iso)
        end_dt = to_pt(end_iso)

        # Clean and parse title
        clean_title = re.sub(r'(?i)^show\s*[-–—]\s*', '', raw_title).strip()
        artist_list = [a.strip() for a in clean_title.split(",") if a.strip()]
        headliner = artist_list[0] if artist_list else ""
        supporters = artist_list[1:]

        row_dict = {
            "Venue": "Tamarack",
            "Date": start_dt.strftime("%a, %B %d") if start_dt else "",
            "Start Time": start_dt.strftime("%-I:%M %p") if start_dt else "",
            "End Time": end_dt.strftime("%-I:%M %p") if end_dt else "",
            "Start DateTime": start_dt,
            "End DateTime": end_dt,
            "Title": clean_title,
            "Image URL": "https://images.squarespace-cdn.com/content/v1/51248e09e4b0b5151b7cb1e1/1573600982044-BK75SW9US5I27XN56G8Z/Tamarack_Teachers.jpg?format=1500w",  # no image available from Google Calendar
            "Event URL": html_link,
            "Headliner": headliner,
        }

        for i, band in enumerate(supporters):
            row_dict[f"Supporting Band {i+1}"] = band

        rows.append(row_dict)

    return pd.DataFrame(rows)
