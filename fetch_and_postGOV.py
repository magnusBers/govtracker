import requests
from requests.auth import HTTPBasicAuth
import datetime

# --- CONFIGURATION ---
WORDPRESS_URL = "https://YOUR-WORDPRESS-SITE.com"
USERNAME = "Daniel Bernal"
APP_PASSWORD = "ikfbsmyssi73ycy5"  # Generated from WordPress -> Profile -> Application Passwords
CUTOFF_DATE = "2024-07-04"  # Only fetch items after this date

# --- POST TO WORDPRESS ---
def create_wp_post(title, content):
    post = {
        "title": title,
        "content": content,
        "status": "publish"
    }
    r = requests.post(
        f"{WORDPRESS_URL}/wp-json/wp/v2/posts",
        auth=HTTPBasicAuth(USERNAME, APP_PASSWORD),
        json=post
    )
    if r.status_code == 201:
        print(f"✅ Posted: {title}")
    else:
        print(f"⚠️ Failed ({r.status_code}): {r.text}")

# --- FETCH LAWS ---
def fetch_laws():
    url = "https://www.legislation.gov.uk/ukpga/data.feed"
    response = requests.get(url)
    if response.status_code != 200:
        print("Failed to fetch laws feed")
        return []
    from xml.etree import ElementTree
    xml = ElementTree.fromstring(response.content)
    for entry in xml.findall("{http://www.w3.org/2005/Atom}entry"):
        title = entry.find("{http://www.w3.org/2005/Atom}title").text
        link = entry.find("{http://www.w3.org/2005/Atom}link").attrib.get("href", "")
        updated = entry.find("{http://www.w3.org/2005/Atom}updated").text
        if updated < CUTOFF_DATE:
            continue
        create_wp_post(title, f"<a href='{link}' target='_blank'>View law</a>")

# --- FETCH POLICIES ---
def fetch_policies():
    url = "https://www.gov.uk/api/search.json?filter_format=policy_paper&order=public_timestamp:desc&filter_public_timestamp>=2024-07-04"
    data = requests.get(url).json()
    for r in data.get("results", []):
        title = r["title"]
        link = "https://www.gov.uk" + r["link"]
        create_wp_post(title, f"<a href='{link}' target='_blank'>Read on GOV.UK</a>")

# --- FETCH SPENDING ---
def fetch_spending():
    url = "https://data.gov.uk/api/3/action/package_search?q=spend+over+25000"
    data = requests.get(url).json()
    for r in data["result"]["results"]:
        title = r["title"]
        link = r["resources"][0]["url"] if r["resources"] else ""
        create_wp_post(title, f"<a href='{link}' target='_blank'>Download dataset</a>")

# --- MAIN ---
if __name__ == "__main__":
    print("Fetching latest government data...")
    fetch_laws()
    fetch_policies()
    fetch_spending()
    print("✅ Done.")
