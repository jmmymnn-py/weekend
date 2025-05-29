import os
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import pytz

from scrape_Gilman import scrape_Gilman
from scrape_Elis import scrape_Elis
from scrape_Stork import scrape_Stork
from combine import combine
from enrich import enrich

CACHE_FILE = "cached_df.csv"
TIMESTAMP_FILE = "cached_df_timestamp.txt"
MAX_AGE_HOURS = 24

def load_bandcamp_lookup():
    bandcamp_df = pd.read_csv("bandcamp.csv")
    bandcamp_df = bandcamp_df.drop_duplicates(subset="band", keep="first")
    return bandcamp_df.set_index("band").to_dict(orient="index")

def need_cache():
    if not os.path.exists(CACHE_FILE) or not os.path.exists(TIMESTAMP_FILE):
        return True
    try:
        with open(TIMESTAMP_FILE, "r") as f:
            cached_time = datetime.fromisoformat(f.read().strip())
        return datetime.now() - cached_time > timedelta(hours=MAX_AGE_HOURS)
    except:
        return True

def refresh_data():
    st.info("Refreshing data from all sources...")
    bandcamp_lookup = load_bandcamp_lookup()
    df = combine(scrape_Gilman(), scrape_Elis(), scrape_Stork())
    df = enrich(df, bandcamp_lookup)
    df.to_csv(CACHE_FILE, index=False)
    with open(TIMESTAMP_FILE, "w") as f:
        f.write(datetime.now().isoformat())
    return df

def load_data(force=False):
    if force or need_cache():
        return refresh_data()
    else:
        return pd.read_csv(CACHE_FILE)

def get_last_updated():
    if os.path.exists(TIMESTAMP_FILE):
        try:
            with open(TIMESTAMP_FILE, "r") as f:
                return datetime.fromisoformat(f.read().strip())
        except:
            return None
    return None

# Streamlit setup
st.set_page_config(layout="wide", page_title="Upcoming Shows")
st.title("Upcoming Shows")
st.caption("Live scraped from Eli's Mile High Club, Thee Stork Club, 924 Gilman.")
st.caption("See ya in the crowd! 📸 @jimmyhadalittlelamb")
# Controls
col1, col2 = st.columns([4, 1])
with col1:
    last_updated = get_last_updated()
    if last_updated:
        st.caption(f"Last updated: {last_updated.strftime('%b %d, %Y %I:%M %p')}")
    else:
        st.caption("No cached timestamp found.")
with col2:
    if st.button("🔁 Force Refresh"):
        df_Master = refresh_data()
    else:
        df_Master = load_data()

# Days out slider
days_out = st.slider("Show events up to how many days from today?", min_value=1, max_value=30, value=7)

# Parse, filter, and sort datetime
df_Master["Start DateTime"] = pd.to_datetime(df_Master["Start DateTime"], errors='coerce')
df_Master = df_Master.dropna(subset=["Start DateTime"])
df_Master = df_Master.sort_values("Start DateTime")

# Timezone-aware filter
local_tz = df_Master["Start DateTime"].dt.tz or pytz.timezone("America/Los_Angeles")
today = datetime.combine(datetime.today(), datetime.min.time()).astimezone(local_tz)
cutoff = today + timedelta(days=days_out)
df_Master = df_Master[df_Master["Start DateTime"].between(today, cutoff)]

# Display grouped by date
for date, group in df_Master.groupby(df_Master["Start DateTime"].dt.date):
    st.header(date.strftime("%A, %B %d"))

    for _, row in group.iterrows():
        st.markdown("---")
        with st.container():
            cols = st.columns([2, 4])
            with cols[0]:
                image_url = row.get("Image URL", "")
                if pd.notna(image_url) and image_url:
                    st.image(image_url, use_container_width=True)

            with cols[1]:
                st.subheader("🎤 "+row["Headliner"])

                # Cleaned supporting list
                support_bands = [
                    row.get("Supporting Band 1", ""),
                    row.get("Supporting Band 2", ""),
                    row.get("Supporting Band 3", "")
                ]
                support = ", ".join([b for b in support_bands if pd.notna(b) and b.strip()])
                if support:
                    st.text(f"➕ Supporting: {support}")

                st.text(f"📍 Venue: {row.get('Venue', '')}")
                st.text(f"🕗 Time: {row['Start DateTime'].strftime('%I:%M %p')}")
                # more info
                more_info = row.get("More Info", "")
                if pd.isna(more_info) or not more_info.strip():
                    st.markdown("**More Info:** Bandcamp not found")
                else:
                    lines = [line.strip() for line in more_info.strip().split("\n") if line.strip()]
                    output = []
                    i = 0
                    while i < len(lines):
                        line = lines[i]
                        if ":" in line and ".bandcamp.com" in line:
                            band_name, url = line.split(":", 1)
                            url = url.strip()
                            location, tags = "N/A", "N/A"
                            j = i + 1
                            while j < len(lines) and not (".bandcamp.com" in lines[j]):
                                if lines[j].lower().startswith("location:"):
                                    location = lines[j].split(":", 1)[1].strip()
                                elif lines[j].lower().startswith("tags:"):
                                    tags = lines[j].split(":", 1)[1].strip()
                                j += 1
                            bullet = f"<li><b>{band_name.strip()}</b> ({location}): <a href='{url}' target='_blank'>{url}</a> [{tags}]</li>"
                            output.append(bullet)
                            i = j
                        else:
                            i += 1
                    html_output = "<ul>" + "".join(output) + "</ul>"
                    st.markdown("🎵 **More Info:**<br>" + html_output, unsafe_allow_html=True)



                if row.get("Event URL"):
                    st.markdown(f"[🎟 Buy Tickets]({row['Event URL']})", unsafe_allow_html=True)
