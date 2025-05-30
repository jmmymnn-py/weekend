import os
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st

from scrape_Gilman import scrape_Gilman
from scrape_Elis import scrape_Elis
from scrape_Stork import scrape_Stork
from scrape_Tamarack import scrape_Tamarack
from combine import combine
from enrich import enrich

CACHE_FILE = "cached_df.csv"
TIMESTAMP_FILE = "cached_df_timestamp.txt"
MAX_AGE_HOURS = 24

def load_bandcamp_lookup(): # --> future: extend to creating lookups of any csv passed to it for access speed.
    bandcamp_df = pd.read_csv("bandcamp.csv")
    bandcamp_df = bandcamp_df.drop_duplicates(subset="band", keep="first")
    return bandcamp_df.set_index("band").to_dict(orient="index")

def need_cache():
    '''checks if you need a cache file -- based on if it's not present or old'''
    if not os.path.exists(CACHE_FILE) or not os.path.exists(TIMESTAMP_FILE):
        return True
    try:
        with open(TIMESTAMP_FILE, "r") as f:
            cached_time = datetime.fromisoformat(f.read().strip())
        return datetime.now() - cached_time > timedelta(hours=MAX_AGE_HOURS)
    except:
        return True

def create_cache():
    progress_bar = st.empty()
    progress_value = 0

    def update_progress(message, step=10):
        nonlocal progress_value
        progress_value += step
        progress_bar.progress(progress_value / 100, text=message)

    update_progress("Indexing Bands (bandcamp_lookup)...", step=5)
    bandcamp_lookup = load_bandcamp_lookup()

    list_scrapeDFs = []

    update_progress("Scraping Gilman...", step=10)
    list_scrapeDFs.append(scrape_Gilman())

    update_progress("Scraping Stork...", step=10)
    list_scrapeDFs.append(scrape_Stork())

    update_progress("Scraping Eli's...", step=10)
    list_scrapeDFs.append(scrape_Elis())

    update_progress("Scraping Tamarack...", step=10)
    list_scrapeDFs.append(scrape_Tamarack())

    update_progress("Merging Events...", step=10)
    df = combine(*list_scrapeDFs)

    update_progress("Enriching w/ Bandcamp...", step=5)

    def enrich_progress_callback(current, total, band_name):
        percent = 55 + int((current / total) * 35)  # progress from 55% to 90%
        progress_bar.progress(percent / 100, text=f"Searching Bandcamp for: {band_name} ({current}/{total})")

    df = enrich(df, bandcamp_lookup, progress_callback=enrich_progress_callback)

    update_progress("Saving to cache...", step=5)
    df.to_csv(CACHE_FILE, index=False)
    with open(TIMESTAMP_FILE, "w") as f:
        f.write(datetime.now().isoformat())

    progress_bar.progress(1.0, text="Done!")  # set to 100%
    # time.sleep(0.5)  # optional: pause briefly so user sees "Done!"
    progress_bar.empty()  # remove the progress bar from UI

    return df

def read_cache(force=False):
    if force or need_cache():
        return create_cache()
    else:
        return pd.read_csv(CACHE_FILE)

def when_updated():
    if os.path.exists(TIMESTAMP_FILE):
        try:
            with open(TIMESTAMP_FILE, "r") as f:
                return datetime.fromisoformat(f.read().strip())
        except:
            return None
    return None
