import re
import sys
from pathlib import Path
import patch_sliqserver_address as patcher


def safe_replace_once(text, pattern, replacement, label):
    new_text, count = re.subn(pattern, lambda _m: replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"Could not patch {label}: expected 1 match, got {count}")
    return new_text


patcher.replace_once = safe_replace_once

if len(sys.argv) != 3 or sys.argv[1] not in {"windows", "android"}:
    raise SystemExit("Usage: apply_address_patch.py windows|android <source-file>")

path = Path(sys.argv[2])
if sys.argv[1] == "windows":
    patcher.patch_windows(path)
else:
    patcher.patch_android(path)

print(f"Applied simplified server address UI: {path}")
