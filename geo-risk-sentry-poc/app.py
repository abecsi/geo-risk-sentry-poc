# Streamlit Cloud entry point (the deployment points at this path); the app itself lives in the repo root.
import pathlib
import runpy

runpy.run_path(str(pathlib.Path(__file__).resolve().parent.parent / "app.py"), run_name="__main__")
