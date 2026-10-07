"""Save a public, key-free DGS10 snapshot for the separate HAR calendar audit.

Run explicitly to retrieve data; model execution uses the saved snapshot offline.
"""
import hashlib
import io
import json
import ssl
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd
import certifi

ROOT = Path(__file__).resolve().parents[1]
cfg = json.loads((ROOT / "config/var_har_notebook.json").read_text())
last_date = pd.to_datetime(pd.read_csv(ROOT / cfg["source"], usecols=["date"])["date"]).max()
url = "https://fred.stlouisfed.org/graph/fredgraph.csv?" + urlencode(
    {"id": "DGS10", "cosd": cfg["sample_start"], "coed": str(last_date.date())})
with urlopen(url, timeout=45, context=ssl.create_default_context(cafile=certifi.where())) as response:
    payload = response.read()
frame = pd.read_csv(io.BytesIO(payload))
if len(frame.columns) != 2 or frame.columns[1] != "DGS10":
    raise ValueError("Unexpected FRED CSV schema")
dates = pd.to_datetime(frame.iloc[:, 0], errors="raise")
values = pd.to_numeric(frame.DGS10.replace(".", None), errors="raise")
if not dates.is_unique or not dates.is_monotonic_increasing or values.notna().sum() == 0:
    raise ValueError("Invalid DGS10 snapshot")
path = ROOT / "datasets/raw/fred_dgs10_2011_2026.csv"
path.parent.mkdir(parents=True, exist_ok=True)
path.write_bytes(payload)
metadata = {
    "series": "DGS10", "source": "Board of Governors of the Federal Reserve System, via FRED",
    "series_url": "https://fred.stlouisfed.org/series/DGS10", "download_url": url,
    "retrieved_at": pd.Timestamp.now(tz="Europe/Amsterdam").isoformat(),
    "units": "Percent per annum; daily, not seasonally adjusted",
    "first_date": str(dates.min().date()), "last_date": str(dates.max().date()),
    "rows": len(frame), "missing_yields": int(values.isna().sum()),
    "path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(payload).hexdigest(),
    "purpose": "Audit the latest HAR yield-joined calendar; not a VAR regressor",
    "vintage_note": "Retrieved snapshot; not historical real-time vintages. No missing values imputed."
}
(ROOT / "datasets/fred_dgs10_manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
print(f"Saved {len(frame)} DGS10 rows ({values.isna().sum()} missing) to {path.relative_to(ROOT)}")
