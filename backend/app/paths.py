"""Where the app keeps its files. The desktop shell overrides these through the environment."""

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

# Everything the app stores: the database, the downloaded speech models, and the voice cache.
DATA_DIR = Path(os.environ.get("SOS_MY_ENGLISH_DATA_DIR") or BACKEND_DIR / "data")

# The built frontend (`npm run build`), served by the backend when it exists.
FRONTEND_DIST = Path(os.environ.get("SOS_MY_ENGLISH_FRONTEND_DIST") or BACKEND_DIR.parent / "frontend" / "dist")

# Hugging Face's default (Xet) transfer first collects a large file in a cache of its own under
# ~/.cache/huggingface. Plain downloads go straight into the folder they are asked to, which
# keeps everything inside DATA_DIR and lets the download's progress be seen. This is read when
# huggingface_hub is first imported, so it is set here, in the first module the app loads.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
