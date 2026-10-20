# Streamlit Cloud entry point (the deployment points at this path); the app itself lives in the repo root.
import pathlib
import runpy
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # so the root app can import risk_model
runpy.run_path(str(ROOT / "app.py"), run_name="__main__")
