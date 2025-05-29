import os
import re
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

def extract_bandcamp_info(band_name):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=options)

    search_url = f"https://bandcamp.com/search?q={band_name.replace(' ', '+')}&item_type=b"
    driver.get(search_url)
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    result = soup.find("div", class_="result-info")

    info = {
        "band": band_name,
        "bandcamp_url": None,
        "location": None,
        "genre": None,
        "tags": []
    }

    if result:
        subhead = result.find("div", class_="subhead")
        info["location"] = subhead.text.strip() if subhead else None

        itemurl = result.find("div", class_="itemurl")
        raw_url = itemurl.a['href'] if itemurl and itemurl.a else ""
        match = re.search(r"(https://[a-z0-9\-]+\.bandcamp\.com)", raw_url)
        info["bandcamp_url"] = match.group(1) if match else raw_url.split('?')[0]

        genre_tag = result.find("div", class_="genre")
        info["genre"] = genre_tag.text.replace("genre:", "").strip() if genre_tag else None

        tags_div = result.find("div", class_="tags")
        if tags_div:
            raw_tags = tags_div.get_text(separator=",").replace("tags:", "")
            info["tags"] = [tag.strip() for tag in raw_tags.split(",") if tag.strip()]

    driver.quit()
    return info

def enrich_missing_band(band_name, bandcamp_df, csv_path="bandcamp.csv"):
    info = extract_bandcamp_info(band_name)
    new_row = {
        "band": band_name,
        "location": info["location"],
        "bandcamp_url": info["bandcamp_url"],
        "genre": info["genre"],
        "tags": ", ".join(info["tags"])
    }
    bandcamp_df = pd.concat([bandcamp_df, pd.DataFrame([new_row])], ignore_index=True)
    bandcamp_df.to_csv(csv_path, index=False)
    return new_row, bandcamp_df

def enrich(df, bandcamp_lookup, csv_path="bandcamp.csv"):
    """
    Enriches the 'More Info' column of the DataFrame with Bandcamp info.
    If info is missing, it scrapes Bandcamp and updates bandcamp.csv.

    Parameters:
        df (pd.DataFrame): Event data
        bandcamp_lookup (dict): band_name -> metadata
        csv_path (str): Path to bandcamp.csv

    Returns:
        pd.DataFrame: Enriched event data
    """
    if os.path.exists(csv_path):
        bandcamp_df = pd.read_csv(csv_path)
    else:
        bandcamp_df = pd.DataFrame(columns=["band", "location", "bandcamp_url", "genre", "tags"])

    def enrich_band_info(band_name):
        nonlocal bandcamp_df, bandcamp_lookup

        if pd.isna(band_name) or band_name.strip() == "":
            return ""
        band_name = band_name.strip()

        band_info = bandcamp_lookup.get(band_name)

        if not band_info or pd.isna(band_info.get("bandcamp_url")):
            new_info, bandcamp_df = enrich_missing_band(band_name, bandcamp_df, csv_path)
            bandcamp_lookup[band_name] = new_info
            band_info = new_info

        if not band_info.get("bandcamp_url"):
            return f"\n{band_name}: No Bandcamp found"

        return (
            f"\n{band_name}: {band_info.get('bandcamp_url', '')}"
            f"\nGenre: {band_info.get('genre', '') or 'N/A'}"
            f"\nTags: {band_info.get('tags', '') or 'N/A'}"
            f"\nLocation: {band_info.get('location', '') or 'N/A'}"
        )

    for idx, row in df.iterrows():
        enrichments = ""
        for col in ["Headliner", "Supporting Band 1", "Supporting Band 2", "Supporting Band 3"]:
            enrichments += enrich_band_info(row.get(col, ""))
        df.at[idx, "More Info"] = (row.get("More Info", "") or "") + enrichments

    return df
