"""Deterministic, audited executive reporting from *already-filtered* commercial metrics.

The saved HTML report is offline/printable and does not contain raw transaction
rows. Raw user content is escaped. CSV summary uses the existing guarded helper.
This module does not mutate source or calculations and requires no new packages.
"""
from __future__ import annotations

from datetime import datetime, timezone
from html import escape
import math
from typing import Mapping

import pandas as pd

from business_metrics import revenue_by_period
from performance_insights import category_profitability


def _finite(value: object) -> float:
    try:
        amount = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Report contains an invalid numeric value.") from exc
    if not math.isfinite(amount):
        raise ValueError("Report contains a non-finite financial value.")
    return amount


def _fmt(value: object, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "Not available"
    return f"{_finite(value):,.{digits}f}"


def _pct(value: object) -> str:
    if value is None or pd.isna(value):
        return "Not defined"
    return f"{_finite(value):,.2f}%"


def _e(value: object) -> str:
    return escape(str(value), quote=True)


def _html_table(frame: pd.DataFrame, *, max_rows: int = 20) -> str:
    if frame.empty:
        return '<p class="muted">No valid observations are available for this section.</p>'
    header = "".join(f"<th>{_e(c)}</th>" for c in frame.columns)
    rows = []
    for row in frame.head(max_rows).itertuples(index=False, name=None):
        cells = []
        for value in row:
            if value is None or pd.isna(value):
                display = "—"
            elif isinstance(value, int) and not isinstance(value, bool):
                display = f"{value:,}"
            elif isinstance(value, float):
                display = _fmt(value)
            else:
                display = _e(value)
            cells.append(f"<td>{display}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return ("<div class='table-wrap'><table><thead><tr>" + header +
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def _profitability_groups(source: pd.DataFrame, calculations: pd.DataFrame, dimension: str) -> pd.DataFrame:
    if dimension not in source.columns:
        raise ValueError("Selected report category is not in the filtered source.")
    if "Mapped Costs" in calculations.columns:
        groups = category_profitability(source, calculations, dimension)
        return groups
    # When no costs were mapped, do not invent profit or profit margin.
    groups = pd.DataFrame({
        "Category": source[dimension].reset_index(drop=True).astype("string").fillna("(Missing)"),
        "Net Revenue": calculations["Net Revenue"].reset_index(drop=True),
    })
    return (groups.groupby("Category", as_index=False, dropna=False)["Net Revenue"]
            .sum().sort_values("Net Revenue", ascending=False, kind="stable")
            .reset_index(drop=True))


def build_executive_report(
    source: pd.DataFrame,
    calculations: pd.DataFrame,
    totals: Mapping[str, object],
    *, dataset_name: str,
    category: str | None,
    date_column: str | None,
    period: str,
    field_mapping: Mapping[str, object],
    filter_notes: str,
    currency_label: str = "Currency not specified",
    generated_at: datetime | None = None,
) -> dict:
    """Return a standalone HTML report plus audit-ready summary/group/time tables.

    Input rows must match in order. Explicit, finite totals must reconcile
    against row-level calculations; otherwise reporting is blocked.
    """
    if source.empty:
        raise ValueError("No filtered rows remain for the report.")
    if len(source) != len(calculations):
        raise ValueError("Filtered source and calculated rows do not align.")
    if not source.columns.is_unique or not calculations.columns.is_unique:
        raise ValueError("Duplicate column names prevent a reliable report.")
    if "Net Revenue" not in calculations:
        raise ValueError("Net Revenue calculation is missing.")
    if period not in ("Monthly", "Quarterly", "Yearly"):
        raise ValueError("Choose Monthly, Quarterly or Yearly.")
    if category is not None and category not in source.columns:
        raise ValueError("The category field is missing from the filtered data.")
    if date_column is not None and date_column not in source.columns:
        raise ValueError("The date field is missing from the filtered data.")
    for key in ("net_revenue",):
        if key not in totals:
            raise ValueError(f"Required financial total is missing: {key}.")
    if ("Gross Revenue" in calculations.columns) != ("gross_revenue" in totals):
        raise ValueError("Gross revenue rows and total must either both be present or both be unavailable.")
    for column, key in (("Gross Revenue", "gross_revenue"), ("Net Revenue", "net_revenue"),
                        ("Mapped Costs", "mapped_costs"), ("Profit After Mapped Costs", "profit_after_mapped_costs")):
        if column in calculations.columns:
            values = pd.to_numeric(calculations[column], errors="coerce")
            if not values.notna().all() or not values.map(math.isfinite).all():
                raise ValueError(f"Calculated column contains missing or invalid numbers: {column}.")
            if key not in totals or not math.isclose(float(values.sum()), _finite(totals[key]), rel_tol=1e-10, abs_tol=0.01):
                raise ValueError(f"Report totals do not reconcile for {column}.")
    has_cost = "Profit After Mapped Costs" in calculations.columns
    summary_rows = [
        ("Matching transactions", len(source)),
        ("Gross Revenue", _finite(totals["gross_revenue"]) if "gross_revenue" in totals else None),
        ("Net Revenue", _finite(totals["net_revenue"])),
        ("Mapped Costs", _finite(totals["mapped_costs"]) if has_cost else None),
        ("Profit After Mapped Costs", _finite(totals["profit_after_mapped_costs"]) if has_cost else None),
        ("Profit Margin %", _finite(totals["profit_margin_pct"]) if has_cost and totals.get("profit_margin_pct") is not None else None),
        ("Net Business Loss", _finite(totals["net_business_loss"]) if has_cost else None),
    ]
    summary = pd.DataFrame(summary_rows, columns=["Metric", "Value"])
    groups = (_profitability_groups(source, calculations, category)
              if category is not None else pd.DataFrame())
    if not groups.empty:
        if not math.isclose(float(groups["Net Revenue"].sum()), _finite(totals["net_revenue"]),
                            rel_tol=1e-10, abs_tol=.01):
            raise ValueError("Category revenue does not reconcile to source totals.")
        if has_cost and not math.isclose(float(groups["Profit After Mapped Costs"].sum()),
                                         _finite(totals["profit_after_mapped_costs"]), rel_tol=1e-10, abs_tol=.01):
            raise ValueError("Category profit does not reconcile to source totals.")
    periods, missing_dates = (revenue_by_period(source[date_column], calculations["Net Revenue"], period)
                              if date_column is not None else (pd.DataFrame(), 0))
    if date_column is not None:
        valid_dates_revenue = (pd.to_numeric(calculations["Net Revenue"].reset_index(drop=True), errors="raise")
                               [pd.to_datetime(source[date_column].reset_index(drop=True), errors="coerce", format="mixed").notna()]
                               .sum())
        if not math.isclose(float(periods["Revenue"].sum()), float(valid_dates_revenue),
                            rel_tol=1e-10, abs_tol=.01):
            raise ValueError("Time-series revenue does not reconcile to dated source rows.")

    generated = generated_at or datetime.now(timezone.utc)
    if generated.tzinfo is None:
        raise ValueError("Report timestamp must have timezone information.")
    timestamp = generated.astimezone(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    notes = [
        "All numbers use the selected Executive Dashboard filters and financial field mappings.",
        "Profit is after mapped costs, NOT accounting net profit unless all expenses and taxes are included.",
        "Missing/invalid dates are excluded from time analysis only; they remain in headline totals.",
        "No currency conversion is performed; use one consistent monetary unit.",
        "CSV transaction-level audits remain available in Section 03 of Executive Overview.",
    ]
    if not has_cost:
        notes.append("No cost field was mapped. Profit, loss and margin are not reported.")
    if missing_dates:
        notes.append(f"{missing_dates:,} records were omitted from time-series analysis for invalid/missing dates.")
    if category is None:
        notes.append("No category was selected for this report.")
    if date_column is None:
        notes.append("No date column was selected for this report.")
    map_rows = "".join(
        f"<tr><th>{_e(label)}</th><td>{_e(value)}</td></tr>"
        for label, value in field_mapping.items()
    )
    note_html = "".join(f"<li>{_e(item)}</li>" for item in notes)
    kpis = [("Gross Revenue", _fmt(totals["gross_revenue"]) if "gross_revenue" in totals else "Not provided"),
            ("Net Revenue", _fmt(totals["net_revenue"]))]
    if has_cost:
        kpis += [("Mapped Costs", _fmt(totals["mapped_costs"])),
                 ("Profit After Mapped Costs", _fmt(totals["profit_after_mapped_costs"])),
                 ("Margin", _pct(totals.get("profit_margin_pct")))]
    tiles = "".join(f"<div class='tile'><span>{_e(label)}</span><strong>{_e(value)}</strong></div>" for label, value in kpis)
    report = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Python BI Studio — Executive Report</title><style>
:root{{--navy:#142B4A;--ink:#26364A;--muted:#617086;--blue:#2878E5;--paper:#F5F8FC;--line:#DCE5F0}}
*{{box-sizing:border-box}}body{{font-family:Arial,'Segoe UI',sans-serif;margin:0;background:var(--paper);color:var(--ink);line-height:1.5}}
main{{max-width:1160px;margin:24px auto;background:white;padding:40px;border-radius:16px;box-shadow:0 7px 34px #142b4a10}}
.eyebrow{{font-size:12px;letter-spacing:.15em;text-transform:uppercase;color:var(--blue);font-weight:700}}
h1{{font-size:38px;line-height:1.1;letter-spacing:-.04em;color:var(--navy);margin:12px 0}}
h2{{font-size:21px;color:var(--navy);margin:30px 0 11px}}p,.muted{{color:var(--muted)}}
.meta{{border-top:1px solid var(--line);padding-top:16px;margin-top:17px;display:grid;grid-template-columns:repeat(2,1fr);gap:10px}}
.meta b{{color:var(--navy)}}.tiles{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:27px}}
.tile{{background:#F3F7FD;border:1px solid var(--line);border-radius:12px;padding:17px}}
.tile span{{display:block;color:var(--muted);font-size:12px;letter-spacing:.02em}}.tile strong{{color:var(--navy);font-size:25px;display:block;margin-top:7px}}
.table-wrap{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{border-bottom:1px solid var(--line);padding:9px;text-align:left;vertical-align:top}}
thead th{{background:#EDF3FB;color:var(--navy)}}.notes{{background:#F7F9FC;padding:15px 20px;border-left:3px solid var(--blue)}}
footer{{padding-top:30px;color:var(--muted);font-size:11px}}@media(max-width:680px){{main{{margin:0;padding:20px}}.tiles{{grid-template-columns:1fr 1fr}}.meta{{grid-template-columns:1fr}}}}
@media print{{body{{background:white}}main{{box-shadow:none;padding:0;max-width:100%}}.tiles,.tile{{break-inside:avoid}}h2{{break-after:avoid}}}}
</style></head><body><main>
<div class='eyebrow'>Python BI Studio / Executive intelligence</div>
<h1>Business Performance Report</h1>
<p>Financial overview built from a verified mapping of filtered source data.</p>
<div class='meta'><div><b>Dataset</b><div>{_e(dataset_name)}</div></div><div><b>Generated</b><div>{_e(timestamp)}</div></div>
<div><b>Matching source records</b><div>{len(source):,}</div></div><div><b>Currency / unit</b><div>{_e(currency_label)}</div></div>
<div><b>Filter context</b><div>{_e(filter_notes)}</div></div><div><b>Time cadence</b><div>{_e(period)}</div></div></div>
<div class='tiles'>{tiles}</div>
<h2>01. Financial measures</h2>{_html_table(summary)}
<h2>02. Category performance</h2><p>Sorted by revenue. Displaying up to 20 groups; the category CSV contains every group.</p>
{_html_table(groups)}
<h2>03. Revenue by calendar period</h2><p>Observed calendar periods only; empty periods are not treated as zero.</p>
{_html_table(periods)}
<h2>04. Field mapping and assumptions</h2><table><tbody>{map_rows}</tbody></table>
<div class='notes'><ul>{note_html}</ul></div>
<footer>Python BI Studio — report generated from local data; no external service is contacted. Use Print → Save as PDF for a printable copy.</footer>
</main></body></html>"""
    return {
        "html": report.encode("utf-8"),
        "summary": summary,
        "categories": groups,
        "periods": periods,
        "missing_date_rows": missing_dates,
        "matching_rows": len(source),
    }
