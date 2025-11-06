import os, json, requests
from xml.etree import ElementTree

OUTPUT_DIR = "public"
STATE_FILE = "last_run.json"
START_DATE = "2024-07-04"     # Keir Starmer start date
os.makedirs(OUTPUT_DIR, exist_ok=True)
HEADERS = {"User-Agent": "govtracker/1.0"}

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"laws": START_DATE, "policies": START_DATE, "spending": START_DATE}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def write_html(title, body_html):
    safe = "".join(c for c in title if c.isalnum() or c in " -_").rstrip()
    path = os.path.join(OUTPUT_DIR, f"{safe[:80]}.html")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"<h2>{title}</h2>\n{body_html}\n<hr>")
        print("📝", path)
    return path

# ---------- LAWS (Acts + Statutory Instruments) ----------
def fetch_legislation_since(since):
    latest = since
    total = 0
    for feed in ["ukpga", "uksi"]:
        url = f"https://www.legislation.gov.uk/{feed}/data.feed"
        r = requests.get(url, headers=HEADERS)
        if r.status_code != 200:
            print("⚠️  Legislation feed failed:", r.status_code); continue
        xml = ElementTree.fromstring(r.content)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for e in xml.findall("a:entry", ns):
            updated = e.find("a:updated", ns).text[:10]
            if updated <= since:
                continue
            title = e.find("a:title", ns).text
            link = e.find("a:link", ns).attrib.get("href", "")
            write_html(title, f"<p><a href='{link}' target='_blank'>View law</a></p><p><small>{updated}</small></p>")
            latest = max(latest, updated)
            total += 1
    print(f"✅ {total} new laws/regs added")
    return latest

# ---------- GOV.UK POLICY PAPERS (fully paginated) ----------
def fetch_policies_since(since):
    latest = since
    total = 0
    page = 1
    while True:
        url = (
            "https://www.gov.uk/api/search.json?"
            f"filter_document_type=policy_paper&order=public_timestamp:desc&page={page}&count=100&"
            f"filter_public_timestamp>{since}"
        )
        r = requests.get(url, headers=HEADERS)
        if r.status_code != 200:
            print("⚠️ GOV.UK API error", r.status_code); break
        data = r.json()
        results = data.get("results", [])
        if not results:
            break
        for item in results:
            title = item.get("title","(no title)")
            link = "https://www.gov.uk" + item.get("link","")
            date = (item.get("public_timestamp","") or "")[:10]
            if date <= since: continue
            write_html(title, f"<p><a href='{link}' target='_blank'>Read policy</a></p><p><small>{date}</small></p>")
            latest = max(latest, date)
            total += 1
        page += 1
    print(f"✅ {total} policy papers added")
    return latest

# ---------- data.gov.uk SPEND-OVER-25k (full pagination) ----------
def fetch_spending_since(since):
    latest = since
    total = 0
    start = 0
    rows = 100
    while True:
        url = f"https://data.gov.uk/api/3/action/package_search?q=spend+over+25000&rows={rows}&start={start}"
        r = requests.get(url, headers=HEADERS)
        if r.status_code != 200:
            print("⚠️ data.gov.uk error", r.status_code); break
        data = r.json()
        result = data.get("result", {})
        items = result.get("results", [])
        if not items:
            break
        for pkg in items:
            date = (pkg.get("metadata_modified") or pkg.get("metadata_created") or "")[:10]
            if date <= since:
                continue
            title = pkg.get("title","(no title)")
            link = pkg.get("resources",[{}])[0].get("url","")
            write_html(title, f"<p><a href='{link}' target='_blank'>Dataset</a></p><p><small>{date}</small></p>")
            latest = max(latest, date)
            total += 1
        start += rows
        if start >= result.get("count", 0):
            break
    print(f"✅ {total} spending datasets added")
    return latest

def build_index():
    files = sorted([f for f in os.listdir(OUTPUT_DIR) if f.endswith(".html")])
    html = "<h1>All UK Government Laws, Policies & Spending since 2024-07-04</h1><hr>\n"
    for f in files:
        html += f"<a href='{f}' target='_blank'>{f[:-5]}</a><br>\n"
    with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("📄 index.html updated")

# ---------- main ----------
if __name__ == "__main__":
    state = load_state()
    print("🕒 previous state:", state)
    state["laws"] = fetch_legislation_since(state["laws"])
    state["policies"] = fetch_policies_since(state["policies"])
    state["spending"] = fetch_spending_since(state["spending"])
    save_state(state)
    build_index()
    print("✅ finished, current state:", state)
