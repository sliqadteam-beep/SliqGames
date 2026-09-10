import base64
import gzip
from pathlib import Path

root = Path(__file__).with_name("quality_v5")
payload = "".join((root / f"part{i}.txt").read_text(encoding="utf-8").strip() for i in range(1, 6))
source = gzip.decompress(base64.b64decode(payload)).decode("utf-8")
exec(compile(source, __file__, "exec"))
