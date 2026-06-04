from pathlib import Path
import re
root = Path(__file__).resolve().parent
exclude = {'_evolved', '__pycache__'}
updated = []
for path in root.rglob('*.py'):
    if any(part in exclude for part in path.parts):
        continue
    text = path.read_text(encoding='utf-8')
    orig = text
    text = text.replace('from sqlalchemy.orm import declarative_base', 'from sqlalchemy.orm import declarative_base')
    text = re.sub(r'(\b\w+)\.datetime\.utcnow\(\)', r'\1.datetime.now(\1.timezone.utc)', text)
    text = re.sub(r'\bdatetime\.datetime\.utcnow\(\)', 'datetime.datetime.now(datetime.timezone.utc)', text)
    text = re.sub(r'\bdatetime\.utcnow\(\)', 'datetime.now(timezone.utc)', text)
    # add timezone import when needed for from datetime import ...
    if ('datetime.now(timezone.utc)' in text or 'timezone.utc' in text) and 'from datetime import ' in text:
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
        path.write_text(text, encoding='utf-8')
        updated.append(str(path))
print('updated', len(updated), 'files')
for p in updated:
    print(p)
