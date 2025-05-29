# updated scrape stork
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import pytz

def scrape_Stork():
    url = "https://theestorkclub.com/calendar/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
    }

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    pt = pytz.timezone("US/Pacific")

    event_blocks = soup.find_all('div', class_='seetickets-list-event-container')
    events = []

    for block in event_blocks:
        title_tag = block.find('p', class_='fs-18 bold mb-12 title')
        title = title_tag.get_text(strip=True) if title_tag else ''
        event_url = title_tag.a['href'] if title_tag and title_tag.a else ''

        date_tag = block.find('p', class_='fs-18 bold mt-1r date')
        date_str = date_tag.get_text(strip=True) if date_tag else ''

        time_tag = block.find('p', class_='fs-12 doortime-showtime')
        time_span = time_tag.find('span') if time_tag else None
        start_time_str = time_span.get_text(strip=True) if time_span else ''

        start_dt = None
        try:
            date_obj = datetime.strptime(date_str + ' 2025', '%a %b %d %Y')
            start_time_obj = datetime.strptime(start_time_str, '%I:%M%p').time()
            start_dt_naive = datetime.combine(date_obj.date(), start_time_obj)
            start_dt = pt.localize(start_dt_naive)
        except Exception:
            start_dt = None

        # Band info
        bands = [band.strip() for band in title.split(',')]
        headliner = bands[0] if bands else ''
        supporting_bands = bands[1:] if len(bands) > 1 else []
        supporting_bands += [''] * (3 - len(supporting_bands))

        # Image
        image_container = block.find('div', class_='seetickets-list-view-event-image-container')
        image_tag = image_container.find('img') if image_container else None
        image_url = image_tag['src'] if image_tag and image_tag.get('src') else ''

        events.append({
            'Venue': 'Thee Stork Club',
            'Date': start_dt.strftime("%a, %B %d") if start_dt else '',
            'Start Time': start_dt.strftime('%-I:%M %p') if start_dt else '',
            'End Time': '',
            'Start DateTime': start_dt,
            'End DateTime': '',
            'Title': title,
            'Image URL': image_url,
            'Event URL': event_url,
            'Headliner': headliner,
            'Supporting Band 1': supporting_bands[0],
            'Supporting Band 2': supporting_bands[1],
            'Supporting Band 3': supporting_bands[2],
        })

    cols = ['Venue', 'Date', 'Start Time', 'End Time',
            'Start DateTime', 'End DateTime', 'Title', 'Image URL',
            'Event URL', 'Headliner', 'Supporting Band 1',
            'Supporting Band 2', 'Supporting Band 3']

    return pd.DataFrame(events)[cols]
