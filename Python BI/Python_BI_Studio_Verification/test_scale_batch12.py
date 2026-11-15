"""Full-dataset Explorer regression suite; pure Pandas tests and wiring."""
import ast
from pathlib import Path

import numpy as np
import pandas as pd

from full_dataset_engine import (
    MAX_EXPORT_ROWS, build_filter_mask, explore_dataset,
    literal_search_mask, safe_preview,
)
from benchmark_explorer import make_synthetic

ROOT = Path(__file__).resolve().parent


def raises(fn):
    try:
        fn()
    except (TypeError, ValueError):
        return
    raise AssertionError("Expected an invalid-input error")


def run():
    df = pd.DataFrame({
        "Product": ["Mouse", "Monitor", "Laptop", "Mouse", None, "LAPTOP"],
        "Sales": [10, 60, 150, 25, np.nan, 240],
        "Notes": ["s+?", "ordinary", "a.b", None, "", "Matched"],
    }, index=[6, 6, 2, 2, 2, 6])
    backup = df.copy(deep=True)
    selected = df.columns.tolist()
    mask = literal_search_mask(df, selected, "s+?", chunk_size=2)
    assert mask.tolist() == [True, False, False, False, False, False]
    assert literal_search_mask(df, selected, "a.b", chunk_size=1).sum() == 1
    assert literal_search_mask(df, selected, "LAPTOP", chunk_size=2).sum() == 2
    assert literal_search_mask(df, selected, "absent", chunk_size=2).sum() == 0
    assert literal_search_mask(df, selected, "", chunk_size=2).sum() == len(df)

    mask = build_filter_mask(df, selected, "Laptop", category_column="Product",
                             category_values=["Laptop"], numeric_column="Sales", minimum=100, maximum=200)
    assert np.flatnonzero(mask).tolist() == [2]
    none = build_filter_mask(df, selected, category_column="Product", category_values=[])
    assert not none.any()
    preview, export, meta = explore_dataset(df, selected, search_text="LAPTOP", sort_column="Sales", ascending=False,
                                            preview_limit=1, export_limit=2, chunk_size=2)
    assert meta.matched_rows == 2 and meta.shown_rows == 1 and meta.exported_rows == 2
    assert export.Sales.tolist() == [240.0, 150.0]
    assert meta.export_truncated is False and meta.search_scope == "Entire active dataset"
    pd.testing.assert_frame_equal(df, backup)
    display = safe_preview(df.iloc[:3])
    assert isinstance(display.iloc[0]["Product"], str)
    assert len(display) == 3

    raises(lambda: explore_dataset(df, ["Unknown"]))
    raises(lambda: explore_dataset(df, selected, preview_limit=1001))
    raises(lambda: explore_dataset(df, selected, export_limit=50001))
    raises(lambda: explore_dataset(df, selected, numeric_column="Sales", minimum=3, maximum=1))
    raises(lambda: literal_search_mask(df, selected, "L", chunk_size=0))
    raises(lambda: explore_dataset(df.rename(columns={"Product": "Sales"}), ["Sales"]))
    raises(lambda: explore_dataset(df, selected, sort_column="missing"))

    # Small sentinel-appears-at-end case proves preview is applied AFTER filter.
    synthetic = make_synthetic(1_001)
    before = synthetic.tail(1).copy(deep=True)
    sentinel = "SPECIAL-ROW-000001000"
    view, result, meta = explore_dataset(synthetic, ["Customer Name", "Sales"], search_text=sentinel,
                                        preview_limit=10)
    assert meta.matched_rows == 1 and view["Customer Name"].iloc[0] == sentinel
    pd.testing.assert_frame_equal(synthetic.tail(1), before)
    # Export cap must not hide that the result set is larger.
    big = pd.DataFrame({"A": np.arange(50_011)})
    view, exported, meta = explore_dataset(big, ["A"], preview_limit=10, export_limit=MAX_EXPORT_ROWS)
    assert meta.matched_rows == 50_011 and len(exported) == MAX_EXPORT_ROWS and meta.export_truncated
    assert len(view) == 10

    app = (ROOT / "app.py").read_text(encoding="utf-8")
    ast.parse(app)
    assert "from explorer_workspace import render_explorer_workspace" in app
    assert "render_explorer_workspace(df)" in app
    assert 'elif workspace_mode == "Prepare & Validate":' in app
    assert 'elif page == "Investment Intelligence":' in app
    assert "render_executive_dashboard(" in app
    assert "save_active_dataset(uploaded_file)" in app
    assert (ROOT / "explorer_workspace.py").is_file()
    print("PASS: Entire-source search, bounded preview/export, filters, duplicates, source immutability, UI wiring")


if __name__ == "__main__":
    run()
