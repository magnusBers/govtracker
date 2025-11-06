import requests
import os
from xml.etree import ElementTree

# --- CONFIGURATION ---
CUTOFF_DATE = "2024-07-04"  # Only fetch items after this date
OUTPUT_DIR = "public"

# --- WRITE HTML FILES ---
def create_html_post(title, content):
    """Save each record as a small HTML file inside /public"""
    safe_title = "".join(c for c in title if c.isalnum() or c in " -_").rstrip()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = os.path.join(OUTPUT_DIR, f"{safe_title[:50]}.html")

    html = f"<h2>{title}</h2>\n<p>{content}</p>\n<hr>"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"📝  Saved: {filename}")

# --- FETCH LAWS ---
def fetch_laws():
    url = "https://www.legislation.gov.uk/ukpga/data.feed"
    r = requests.get(url)
    if r.status_code != 200:
        print("⚠️  Failed to fetch laws feed"); return
    xml = ElementTree.fromstring(r.content)
    for e in xml.findall("{http://www.w3.org/2005/Atom}entry"):
        title = e.find("{http://www.w3.org/2005/Atom}title").text
        link = e.find("{http://www.w3.org/2005/Atom}link").attrib.get("href", "")
        updated = e.find("{http://www.w3.org/2005/Atom}updated").text
        if updated < CUTOFF_DATE:
            continue
        create_html_post(title, f"<a href='{link}' target='_blank'>View law</a>")

# --- FETCH POLICIES ---
def fetch_policies():
    url = ("https://www.gov.uk/api/search.json?"
           "filter_format=policy_paper&order=public_timestamp:desc&"
           "filter_public_timestamp>=2024-07-04")
    try:
        data = requests.get(url).json()
    except Exception as e:
        print("⚠️  Failed to fetch policies:", e); return
    for r in data.get("results", []):
        title = r["title"]
        link = "https://www.gov.uk" + r["link"]
        create_html_post(title, f"<a href='{link}' target='_blank'>Read on GOV.UK</a>")

# --- FETCH SPENDING ---
def fetch_spending():
    url = "https://data.gov.uk/api/3/action/package_search?q=spend+over+25000"
    try:
        data = requests.get(url).json()
    except Exception as e:
        print("⚠️  Failed to fetch spending:", e); return
    for r in data.get("result", {}).get("results", []):
        title = r["title"]
        link = r["resources"][0]["url"] if r.get("resources") else ""
        create_html_post(title, f"<a href='{link}' target='_blank'>Download dataset</a>")

# --- BUILD INDEX PAGE ---
def build_index():
    files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".html")]
    index_html = "<h1>Latest Government Data</h1>\n" + "\n".join(
        f"<a href='{f}'>{f}</a><br>" for f in sorted(files, reverse=True)
    )
    with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)
    print("📄  Built index.html")

# --- MAIN ---
if __name__ == "__main__":
    print("Fetching latest government data...")
    fetch_laws()
    fetch_policies()
    fetch_spending()
    build_index()
    print("✅  Done.")
