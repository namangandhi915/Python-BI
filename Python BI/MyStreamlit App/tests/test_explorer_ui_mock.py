"""Mocked Explorer control-flow test (not a substitute for real browser checks)."""
from __future__ import annotations
import sys
import types

import pandas as pd

# Only used when Streamlit is not installed in the test environment.
try:
    import streamlit
except ImportError:
    sys.modules["streamlit"] = types.SimpleNamespace()

import explorer_workspace
from benchmark_explorer import make_synthetic


class Context:
    def __enter__(self):
        return self
    def __exit__(self, *_args):
        return False
    def metric(self, *_args, **_kwargs):
        return None


class FakeUI:
    def __init__(self, term: str):
        self.term = term
        self.metrics = []
        self.downloads = []
        self.tables = []
        self.messages = []
    def caption(self, *args, **kwargs):
        self.messages.extend(args)
    def info(self, *args, **kwargs):
        self.messages.extend(args)
    def warning(self, *args, **kwargs):
        self.messages.extend(args)
    def error(self, *args, **kwargs):
        raise AssertionError("Unexpected UI error: " + str(args))
    def markdown(self, *_a, **_kw):
        return None
    def columns(self, n, **_kw):
        return [self] * n
    def expander(self, *_a, **_kw):
        return Context()
    def metric(self, title, value, **_kw):
        self.metrics.append((title, str(value)))
    def multiselect(self, _label, options, default=None, **kwargs):
        return list(default or [])
    def text_input(self, _label, **kwargs):
        return self.term
    def selectbox(self, _label, options, index=0, **kwargs):
        return list(options)[index]
    def checkbox(self, _label, value=False, **kwargs):
        return value
    def dataframe(self, frame, **kwargs):
        self.tables.append(frame.copy())
    def download_button(self, _label, data, **kwargs):
        self.downloads.append((kwargs.get("file_name"), data))


def run():
    source = make_synthetic(1200)
    before = source.tail(1).copy(deep=True)
    fake = FakeUI("SPECIAL-ROW-000001199")
    explorer_workspace.st = fake
    explorer_workspace.render_explorer_workspace(source)
    assert ("Full-dataset matches", "1") in fake.metrics
    assert ("Records shown", "1") in fake.metrics
    assert fake.tables[0]["Customer Name"].iloc[0] == "SPECIAL-ROW-000001199"
    assert fake.downloads and fake.downloads[0][0] == "python_bi_full_dataset_explorer.csv"
    assert b"SPECIAL-ROW-000001199" in fake.downloads[0][1]
    pd.testing.assert_frame_equal(source.tail(1), before)
    print("PASS: Mocked Explorer UI controls, full-search count, preview and CSV export")


if __name__ == "__main__":
    run()
