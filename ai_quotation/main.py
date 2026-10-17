import os
import sys
from pathlib import Path
import uvicorn

# Configure cache and temp directories on D: to prevent C: drive out-of-space error
base_dir = Path(__file__).resolve().parent
os.chdir(base_dir)
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

cache_dir = base_dir / ".cache"
os.environ.setdefault("HF_HOME", str(cache_dir / "huggingface"))
os.environ.setdefault("FASTEMBED_CACHE_PATH", str(cache_dir / "fastembed"))
temp_dir = cache_dir / "temp"
temp_dir.mkdir(parents=True, exist_ok=True)
(cache_dir / "huggingface").mkdir(parents=True, exist_ok=True)
(cache_dir / "fastembed").mkdir(parents=True, exist_ok=True)
os.environ["TEMP"] = str(temp_dir)
os.environ["TMP"] = str(temp_dir)

print("[INFO] Initializing quotation engine and loading embedding models...", flush=True)

from src.interfaces.web_app import create_app

app = create_app(db_path=str(base_dir / "quotations.db"), auto_seed=True)

if __name__ == "__main__":
    print("[INFO] Engine initialized successfully.", flush=True)
    print("[INFO] QuotationFinder Web App is running at http://localhost:8000", flush=True)
    print("[INFO] (Note: This is a web server. It stays active listening for requests. Press Ctrl+C to stop.)", flush=True)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, app_dir=str(base_dir))

