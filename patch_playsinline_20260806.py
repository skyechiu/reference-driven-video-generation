import re, shutil, datetime

SRC = "pipeline/app.py"
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = f"pipeline/app.py.backup_playsinline_{ts}"
shutil.copy2(SRC, backup)
print("backup:", backup)

with open(SRC, "r", encoding="utf-8") as f:
    src = f.read()
orig_len = len(src)

def add_playsinline(m):
    tag = m.group(0)
    if re.search(r'\bplaysinline\b', tag):
        return tag
    return tag.replace('<video', '<video playsinline', 1)

before = re.findall(r'<video\b[^>]*>', src)
missing_before = len([t for t in before if 'playsinline' not in t])
src, n = re.subn(r'<video\b[^>]*>', add_playsinline, src)
after = re.findall(r'<video\b[^>]*>', src)
missing_after = len([t for t in after if 'playsinline' not in t])

with open(SRC, "w", encoding="utf-8") as f:
    f.write(src)

print("total video tags:", len(before))
print("missing playsinline before/after:", missing_before, "/", missing_after)
print("size:", orig_len, "->", len(src))
