import os
import re
from bs4 import BeautifulSoup
import json

FRONTEND_DIR = r"C:\Users\user\Desktop\visiontrader_ai\frontend"

REQUIRED_EFFECTS = {
    "stars_background": [r"stars", r"twinkling", r"cosmic", r"background-image:.*url.*stars"],
    "frosted_glass": [r"glass", r"backdrop-filter:\s*blur", r"rgba\(.*,.*,.*,\s*0\.[1-9]\)"],
    "neon_glow": [r"neon", r"glow", r"box-shadow:.*rgba\(0,\s*255,\s*255", r"text-shadow"],
    "laser_scanner": [r"laser", r"scanner", r"scan-line"],
    "fade_in_animation": [r"fade-in", r"animate-fade", r"animation:.*fade"],
    "ripple_effect": [r"ripple"]
}

html_files = [f for f in os.listdir(FRONTEND_DIR) if f.endswith('.html')]

report = {
    "total_pages": len(html_files),
    "pages": {},
    "broken_links": [],
    "issues": []
}

for file in html_files:
    file_path = os.path.join(FRONTEND_DIR, file)
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    soup = BeautifulSoup(content, "html.parser")
    
    page_report = {
        "effects": {},
        "buttons": len(soup.find_all("button")),
        "inputs": len(soup.find_all("input")),
        "selects": len(soup.find_all("select")),
        "links": len(soup.find_all("a"))
    }
    
    # Check for effects in HTML content and inline styles
    content_lower = content.lower()
    for effect, patterns in REQUIRED_EFFECTS.items():
        found = False
        for pattern in patterns:
            if re.search(pattern, content_lower):
                found = True
                break
        page_report["effects"][effect] = found
        if not found and effect not in ["laser_scanner"]: # laser is mostly in charts
            report["issues"].append(f"Missing {effect} in {file}")

    # Check links (superficial check)
    for a in soup.find_all("a"):
        href = a.get("href")
        if href and not href.startswith("#") and not href.startswith("http") and not href.startswith("mailto"):
            if not os.path.exists(os.path.join(FRONTEND_DIR, href.split('?')[0].split('#')[0])):
                report["broken_links"].append(f"{file} -> {href}")
                
    report["pages"][file] = page_report

with open(r"C:\Users\user\Desktop\visiontrader_ai\frontend_report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=4)

print("Frontend check complete. Found issues:", len(report["issues"]), "Broken links:", len(report["broken_links"]))
