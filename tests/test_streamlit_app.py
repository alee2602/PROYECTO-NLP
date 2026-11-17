from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app" / "streamlit_app.py")


def test_app_renders_without_exceptions():
    at = AppTest.from_file(APP, default_timeout=120).run()
    assert not at.exception
    assert len(at.tabs) == 2
