import os
import glob
import re

FRONTEND_DIR = r"C:\Users\user\Desktop\visiontrader_ai\frontend"

font_link = '<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&family=Inter:wght@400;600;800&display=swap" rel="stylesheet">'
theme_script = '<script src="js/theme.js"></script>'

def process_html_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content

    # 1. Update Font links
    # Remove old font links for Cairo or Inter
    content = re.sub(r'<link[^>]+family=Cairo[^>]*>', '', content)
    content = re.sub(r'<link[^>]+family=Inter[^>]*>', '', content)
    
    # Inject new font link before </head>
    if font_link not in content:
        content = content.replace("</head>", f"    {font_link}\n</head>")

    # 2. Add theme.js before </body>
    if "js/theme.js" not in content:
        content = content.replace("</body>", f"    {theme_script}\n</body>")

    # 3. Add fade-in to main or app-layout
    if '<main class="main-content">' in content:
        content = content.replace('<main class="main-content">', '<main class="main-content fade-in">')
    elif '<div class="app-layout">' in content:
        content = content.replace('<div class="app-layout">', '<div class="app-layout fade-in">')
    elif '<div class="login-card">' in content:
        content = content.replace('<div class="login-card">', '<div class="login-card fade-in">')

    # Save if changed
    if content != original_content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False

def main():
    html_files = glob.glob(os.path.join(FRONTEND_DIR, "*.html"))
    changed_count = 0
    for file in html_files:
        if process_html_file(file):
            print(f"Updated: {os.path.basename(file)}")
            changed_count += 1
            
    print(f"\nTotal files updated: {changed_count}/{len(html_files)}")

if __name__ == "__main__":
    main()
