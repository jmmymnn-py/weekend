import os
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import pytz

## Importing functions ---------------------------------------------------------------------##

from scrape_Gilman import scrape_Gilman
from scrape_Elis import scrape_Elis
from scrape_Stork import scrape_Stork
from combine import combine
from enrich import enrich
from cache import load_bandcamp_lookup, need_cache, create_cache, read_cache, when_updated
from run_Streamlit import run_Streamlit

CACHE_FILE = "cached_df.csv"
TIMESTAMP_FILE = "cached_df_timestamp.txt"
MAX_AGE_HOURS = 24


## Run Streamlit  ---------------------------------------------------------------------##
run_Streamlit()