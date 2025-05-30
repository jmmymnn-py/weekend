import pandas as pd
import pytz
import streamlit as st
from datetime import datetime, timedelta
from collections import Counter
from cache import create_cache, read_cache, when_updated

# ----------------------------------------------------------------------
#  Location → Emoji mapping
# ----------------------------------------------------------------------

# Explicit country flags and a few quick city fall-backs
FLAG_MAP = {
    "united states": "🇺🇸",
    "usa": "🇺🇸",
    "canada": "🇨🇦",
    "quebec": "🇨🇦",
    "ontario": "🇨🇦",
    "alberta": "🇨🇦",
    "british columbia": "🇨🇦",
    "united kingdom": "🇬🇧",
    "uk": "🇬🇧",
    "germany": "🇩🇪",
    "austria": "🇦🇹",
    "romania": "🇷🇴",
    "france": "🇫🇷",
    "belgium": "🇧🇪",
    "argentina": "🇦🇷",
    "japan": "🇯🇵",
    "brazil": "🇧🇷",
    "mexico": "🇲🇽",
}

# Full list of U.S. state names in lower-case (used to attach 🇺🇸)
USA_STATES = {
    "alabama","alaska","arizona","arkansas","california","colorado","connecticut","delaware",
    "florida","georgia","hawaii","idaho","illinois","indiana","iowa","kansas","kentucky",
    "louisiana","maine","maryland","massachusetts","michigan","minnesota","mississippi",
    "missouri","montana","nebraska","nevada","new hampshire","new jersey","new mexico",
    "new york","north carolina","north dakota","ohio","oklahoma","oregon","pennsylvania",
    "rhode island","south carolina","south dakota","tennessee","texas","utah","vermont",
    "virginia","washington","west virginia","wisconsin","wyoming"
}

# Canadian provinces not already in FLAG_MAP keys
CANADA_PROVS = {
    "alberta","british columbia","manitoba","new brunswick","newfoundland","nova scotia",
    "ontario","prince edward island","Québec","saskatchewan",
}


def location_to_emoji(location: str) -> str:
    """Return an emoji flag (or special icon) for a given free-form location string."""
    if not location or pd.isna(location):
        return "🌐"

    loc = location.lower()

    # Special Oakland / CA rules
    if "oakland" in loc and "california" in loc:
        return "🌳"  # Oakland tree
    if "california" in loc:
        return "🏠"  # generic CA house

    # Canadian provinces – map to 🇨🇦
    if any(prov in loc for prov in CANADA_PROVS):
        return "🇨🇦"

    # Individual U.S. states – map to 🇺🇸
    if any(state in loc for state in USA_STATES):
        return "🇺🇸"

    # Direct country / keyword lookup
    for key, flag in FLAG_MAP.items():
        if key in loc:
            return flag

    return "🌐"  # default globe
def print_Header():
    st.set_page_config(layout="wide", page_title="Upcoming Shows")
    st.title("Upcoming Shows")
    st.caption("Live scraped from Eli's Mile High Club, Thee Stork Club, 924 Gilman.")
    st.caption("See ya in the crowd! 📸 @jimmyhadalittlelamb")
    changelog = "Bandcamp Scrape is experimental -- may not be correct"

    col1, col2 = st.columns([4, 1])
    with col1:
        last_updated = when_updated()
        if last_updated:
            st.caption(f"Last updated: {last_updated.strftime('%b %d, %Y %I:%M %p')}"+ f" | {changelog}")
        else:
            st.caption("No cached timestamp found. "+ f" | {changelog}")
    return col2


def infer_event_genres(df, top_n=3):
    """
    Adds an 'Event Genres' column inferred from artist tag lines.
    """
    inferred = []

    for _, row in df.iterrows():
        tags = []
        # Extract tag lines from More Info
        more = row.get("More Info", "") or ""
        for line in more.split("\n"):
            if line.lower().startswith("tags:"):
                tags += [t.strip().lower()
                         for t in line.split(":", 1)[1].split(",")
                         if t.strip()]
        # Pick most common tags
        common = [t for t, _ in Counter(tags).most_common(top_n)]
        inferred.append(" / ".join(common) if common else "unknown")

    df["Event Genres"] = inferred
    return df


def loadCache_into_Streamlit(force=False, days_out=7):
    df = create_cache() if force else read_cache()
    df["Start DateTime"] = pd.to_datetime(df["Start DateTime"], errors='coerce')
    df = df.dropna(subset=["Start DateTime"])
    df = df.sort_values("Start DateTime")
    df = infer_event_genres(df)

    local_tz = df["Start DateTime"].dt.tz or pytz.timezone("America/Los_Angeles")
    today = datetime.combine(datetime.today(), datetime.min.time()).astimezone(local_tz)
    cutoff = today + timedelta(days=days_out)
    return df[df["Start DateTime"].between(today, cutoff)]


def print_event(row):
    st.markdown("---")
    with st.container():
        cols = st.columns([2, 4])
        with cols[0]:
            genre = f"{row.get('Event Genres', 'unknown')}"
            if genre == "unknown":
                st.caption("")  
            else:
                st.caption(genre)
            
            image_url = row.get("Image URL", "")
            if pd.notna(image_url) and image_url:
                st.image(image_url, use_container_width=True)


        with cols[1]:
            # EVENT Title -------------------------------------------#
            if row.get('Event Genres', 'unknown') == "unknown":
                st.subheader("🍻 " + row["Headliner"])

            else:
                st.subheader("🎤 " + row["Headliner"])
            ## EVENT Supporting Acts -------------------------------------------#
            support_bands = [
                row.get("Supporting Band 1", ""),
                row.get("Supporting Band 2", ""),
                row.get("Supporting Band 3", "")
            ]
            support = ", ".join([b for b in support_bands if pd.notna(b) and b.strip()])
            if support:
                st.markdown(f"➕ Supporting: **{support}**")
            ## EVENT Details - Venue, Time, Ticket Url-------------------------------------------#
            st.text(f"📍 {row.get('Venue', '')}")
            st.text(f"🕗 {row['Start DateTime'].strftime('%I:%M %p')}")
            if row.get("Event URL"):
                st.markdown(f"[🎟 Get Tickets]({row['Event URL']})", unsafe_allow_html=True)
            ## EVENT More Info - Bandcamp Results-------------------------------------------#
            more_info = row.get("More Info", "")
            if pd.isna(more_info) or not more_info.strip():
                st.markdown("**More Info:** Bandcamp not found")
            else:

                lines   = [ln.strip() for ln in more_info.strip().split("\n") if ln.strip()]
                bullets = []
                i = 0
                while i < len(lines):
                    line = lines[i]
                    if ":" in line and ".bandcamp.com" in line:
                        band, url = line.split(":", 1)
                        url = url.strip()
                        loc, tags = "N/A", "N/A"
                        j = i + 1
                        while j < len(lines) and ".bandcamp.com" not in lines[j]:
                            low = lines[j].lower()
                            if low.startswith("location:"):
                                loc  = lines[j].split(":", 1)[1].strip()
                            elif low.startswith("tags:"):
                                tags = lines[j].split(":", 1)[1].strip()
                            j += 1

                        emoji = location_to_emoji(loc)
                        bullets.append(
                            f"<li style='list-style-type:none;'>"
                            f"<b>{band.strip()}</b> | "
                            f"<a href='{url}' target='_blank'>{url[8:]}</a>"

                            # inner list keeps bullets
                            f"<ul style='margin-left:0;padding-left:0;list-style-type:circle;'>"                            
                            f"<li>{emoji} {loc} <i>[{tags}]</i></li></ul></li>"
                        )
                        i = j
                    else:
                        i += 1
            st.markdown("" + "".join(bullets) + "</ul>", unsafe_allow_html=True)

def run_Streamlit():
    col2 = print_Header()
    force_refresh = col2.button("🔁 Force Refresh")
    days_out = st.slider("Show events up to how many days from today?", min_value=1, max_value=30, value=7)
    df_Master = loadCache_into_Streamlit(force=force_refresh, days_out=days_out)

    for date, group in df_Master.groupby(df_Master["Start DateTime"].dt.date):
        st.markdown("----")
        st.header("📅 " + date.strftime("%A, %B %d"))
        for _, row in group.iterrows():
            print_event(row)
