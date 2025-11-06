import requests, os, json
from xml.etree import ElementTree
from datetime import datetime

OUTPUT_DIR = "public"
STATE_FILE = "last_run.json"
START_DATE = "2024-07-04"  # Keir Starmer start date
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Load previous run state ---
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"laws": START_DATE, "policies": START_DATE, "spending": START_DATE}

# --- Save new state ---
def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

# --- Utility to write HTML ---
def create_html(title, content):
    safe_title = "".join(c for c in title if c.isalnum() or c in " -_").rstrip()
    filename = os.path.join(OUTPUT_DIR, f"{safe_title[:60]}.html")
    html = f"<h2>{title}</h2>\n<p>{content}</p>\n<hr>"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"📝  Saved: {filename}")

# --- Fetch Laws incrementally ---
def fetch_laws(since):
    url = "https://www.legislation.gov.uk/ukpga/data.feed"
    r = requests.get(url)
    if r.status_code != 200:
        print("❌ Failed to fetch laws feed"); return since
    xml = ElementTree.fromstring(r.content)
    latest = since
    for e in xml.findall("{http://www.w3.org/2005/Atom}entry"):
        updated = e.find("{http://www.w3.org/2005/Atom}updated").text[:10]
        if updated <= since:
            continue
        title = e.find("{http://www.w3.org/2005/Atom}title").text
        link = e.find("{http://www.w3.org/2005/Atom}link").attrib.get("href", "")
        create_html(title, f"<a href='{link}' target='_blank'>View law</a>")
        if updated > latest:
            latest = updated
    return latest

# --- Fetch GOV.UK policy papers incrementally ---
def fetch_policies(since):
    page = 1
    latest = since
    while True:
        url = (
            "https://www.gov.uk/api/search.json?"
            f"filter_format=policy_paper&order=public_timestamp:desc&page={page}&"
            f"filter_public_timestamp>{since}"
        )
        r = requests.get(url)
        if r.status_code != 200:
            print("❌ Policies fetch failed on page", page); break
        data = r.json()
        results = data.get("results", [])
        if not results:
            break
        for item in results:
            title = item["title"]
            link = "https://www.gov.uk" + item["link"]
            date = item.get("public_timestamp", "")[:10]
            create_html(title, f"<a href='{link}' target='_blank'>Read policy</a>")
            if date > latest:
                latest = date
        page += 1
    return latest

# --- Fetch data.gov.uk spending datasets incrementally ---
def fetch_spending(since):
    start = 0
    rows = 100
    latest = since
    while True:
        url = f"https://data.gov.uk/api/3/action/package_search?q=spend+over+25000&rows={rows}&start={start}"
        r = requests.get(url)
        if r.status_code != 200:
            print("❌ Spending fetch failed"); break
        data = r.json()
        results = data["result"]["results"]
        if not results:
            break
        for res in results:
            title = res["title"]
            link = res["resources"][0]["url"] if res.get("resources") else ""
            date = res.get("metadata_modified", "")[:10]
            if date <= since:
                continue
            create_html(title, f"<a href='{link}' target='_blank'>Download dataset</a>")
            if date > latest:
                latest = date
        start += rows
        if start >= data["result"]["count"]:
            break
    return latest

# --- Build Index ---
def build_index():
    files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".html")]
    files.sort(reverse=True)
    html = "<h1>Latest UK Government Data</h1><hr>\n"
    for f in files:
        html += f"<a href='{f}' target='_blank'>{f.replace('.html','')}</a><br>\n"
    with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("📄  Index updated")

# --- Main ---
if __name__ == "__main__":
    state = load_state()
    print("🕒 Previous run state:", state)

    new_laws = fetch_laws(state["laws"])
    new_policies = fetch_policies(state["policies"])
    new_spending = fetch_spending(state["spending"])

    state["laws"] = max(state["laws"], new_laws)
    state["policies"] = max(state["policies"], new_policies)
    state["spending"] = max(state["spending"], new_spending)

    save_state(state)
    build_index()
    print("✅  Updated data. Current state:", state)
