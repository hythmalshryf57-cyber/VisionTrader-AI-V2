from pathlib import Path
import re
root = Path(__file__).resolve().parent
exclude = {'_evolved', '__pycache__'}
updated = []
py_files = list(root.rglob('*.py'))
for path in py_files:
    if any(part in exclude for part in path.parts):
        continue
    try:
        text = path.read_text(encoding='utf-8')
    except Exception:
        try:
            text = path.read_text(encoding='latin-1')
        except Exception:
            continue
    orig = text
    # SQLAlchemy declarative_base import fix
    text = text.replace('from sqlalchemy.orm import declarative_base', 'from sqlalchemy.orm import declarative_base')
    # Replace common patterns
    text = re.sub(r"\bdatetime\.datetime\.utcnow\(\)", "datetime.datetime.now(datetime.timezone.utc)", text)
    text = re.sub(r"\bdatetime\.utcnow\(\)", "datetime.now(timezone.utc)", text)
    # Replace default/onupdate references to utcnow (callable) -> lambda returning tz-aware now
    text = re.sub(r"default=\s*datetime\.datetime\.utcnow", "default=lambda: datetime.datetime.now(datetime.timezone.utc)", text)
    text = re.sub(r"onupdate=\s*datetime\.datetime\.utcnow", "onupdate=lambda: datetime.datetime.now(datetime.timezone.utc)", text)
    text = re.sub(r"default=\s*datetime\.utcnow", "default=lambda: datetime.now(timezone.utc)", text)
    text = re.sub(r"onupdate=\s*datetime\.utcnow", "onupdate=lambda: datetime.now(timezone.utc)", text)
    # Add timezone to from datetime imports when using timezone
    if ('datetime.now(timezone.utc)' in text or 'datetime.timezone.utc' in text) and 'from datetime import ' in text:
        lines = text.splitlines(True)
        new_lines = []
        modified = False
        for line in lines:
            if line.startswith('from datetime import '):
                if 'timezone' not in line:
                    imports = [p.strip() for p in line[len('from datetime import '):].strip().rstrip('\n').split(',')]
                    if 'timezone' not in imports:
                        imports.append('timezone')
                        line = 'from datetime import ' + ', '.join(sorted(dict.fromkeys(imports))) + '\n'
                        modified = True
            new_lines.append(line)
        if modified:
            text = ''.join(new_lines)
    if text != orig:
        try:
            path.write_text(text, encoding='utf-8')
        except Exception:
            path.write_text(text, encoding='latin-1')
        updated.append(str(path))
print('updated', len(updated), 'files')
for p in updated:
    print(p)
