# Python BI Studio — Enterprise Design System 3.0

This is an original product identity informed by general enterprise UX principles—not a copy of another corporation's website, trademark or proprietary typeface.

## Visual foundation
- Light-background application throughout (`#F6F8FC` canvas, white surfaces, cool grey sidebar).
- Executive navy (`#142B4A`) for important text and branding; restrained blue (`#246ED3`) for actions; green is reserved for positive dataset/metric status; red is reserved for meaningful errors.
- System-first type stack: IBM Plex Sans if legally installed on the user's machine, then Segoe UI / Aptos / Arial. **No font files are shipped**.
- Consistent four-page masthead: Home / Data Workspace / Dashboard / Investment Intelligence, with clearly marked active dataset.
- Data tables remain compact for analysis while application headings, labels and sidebar navigation are larger.
- Accessible focus outlines, minimum form target sizes, responsive Home cards and reduced-motion support.

## Design acceptance checklist (manual)
1. Desktop at standard Windows display scale: full titles and sidebar labels are readable.
2. Browser zoom 100%, 125%, 150%: labels do not overlap, browser scroll works.
3. At narrow width: Home cards stack, sidebar remains available and controls do not horizontally clip.
4. Keyboard Tab navigation provides an obvious focus indicator.
5. Chart Studio, data tables and controls remain legible against the light background.
6. Home and all three analysis workspaces use consistent typographic hierarchy.
7. Product displays the user's actual active dataset name safely; no raw rows are inserted into the masthead.

## Existing functionality preserved
All existing modes and their keys remain unchanged: Dataset Library, Explore, Prepare & Validate, Financial Performance, Business Planning, Executive Dashboard Sections 03–10, legacy view, Investment scenarios and historical market research.

## Known limitations
CSS selectors for Streamlit's internal `data-testid` structure may need maintenance when Streamlit upgrades. Visual acceptance on the user's running Windows Streamlit server is required. The downloaded code was not tested against a real browser in the packaging environment.
