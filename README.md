# Python BI Studio

A local Streamlit business intelligence app for exploring data, building dashboards, comparing periods, and reviewing financial metrics.

## Share the project

Share the [Python BI GitHub repository](https://github.com/namangandhi915/Python-BI) with your professor. The GitHub link contains the source code; it is not a hosted website. To use the app, your professor should clone the repository and run it on their own computer. The app then opens in a browser at `http://127.0.0.1:8501` on that computer.

The repository includes the application, its pinned Python dependencies, a sample workbook, and synthetic demo data. Files a user uploads or saves while working are kept locally in `stored_datasets/` and are not shared through GitHub.

## Run the app on Windows

Install Git and Python 3.13, then open PowerShell and run:

```powershell
git clone https://github.com/namangandhi915/Python-BI.git
cd Python-BI
cd "Python BI\MyStreamlit App"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe start_local.py
```

Open [http://127.0.0.1:8501](http://127.0.0.1:8501). Keep the terminal window open while using the app. The launcher listens on this computer only; it does not publish the app to the internet.

If Python 3.13 is installed but `python` does not select it, use `py -3.13 -m venv .venv` for the virtual environment creation step. The remaining commands stay the same.

## Run the app on macOS or Linux

Install Git and Python 3.13, then open Terminal and run:

```bash
git clone https://github.com/namangandhi915/Python-BI.git
cd Python-BI/"Python BI/MyStreamlit App"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python start_local.py
```

Open [http://127.0.0.1:8501](http://127.0.0.1:8501) and leave the terminal open while using the app.

## Open and close the app later

After the first setup, do not recreate `.venv` or reinstall packages each time. Open a terminal in the `Python BI/MyStreamlit App` folder and run:

- Windows: `.venv\Scripts\python.exe start_local.py`
- macOS/Linux: `.venv/bin/python start_local.py`

Then open `http://127.0.0.1:8501` in a browser. To close the app, focus the terminal running it and press **Ctrl+C**. Closing the browser tab alone does not stop the app; press **Ctrl+C** in the terminal. Start it again with the same command whenever you want to use it.

To update an existing clone, stop the app, open a terminal at the repository root, run `git pull`, then restart it. If `requirements.txt` changed, reinstall dependencies from the app folder using `.venv\Scripts\python.exe -m pip install -r requirements.txt` on Windows or `.venv/bin/python -m pip install -r requirements.txt` on macOS/Linux.

If port 8501 is already in use, check whether another copy of the app is still running and stop it with **Ctrl+C** in its terminal before starting this one.

## Working with datasets

Use **Dataset Library → Add a dataset to the library** to save and activate a CSV or XLSX file locally. In **Data Workspace → Explore**, upload multiple files and select one or more under **Files to analyse together**. New Explorer uploads are also saved locally. Multiple selected files are stacked by matching column names; they are not joined by a key. Fields missing from a file become empty in the combined view. Select one file for separate analysis.

**Prepare & Validate → Platform assurance** contains the quality sample and Explorer preview controls. They are separate limits: the first controls how many rows are checked for the diagnostic, while the second controls how many matching rows Explorer displays. Exact quality scans, large previews, and large exports can take substantial time and memory. Prepared copies automatically trim text whitespace; the source files remain unchanged.

Choose financial fields in **Commercial Intelligence → Financial Performance**. Dashboard calculations use that source's selected mapping or clearly identified suggested fields. Market observation frequency describes the spacing of the uploaded prices; choosing quarterly or yearly does not resample a daily file. Data is processed in memory and uploads are limited to 256 MiB per file, so practical capacity depends on file width, format, browser, and available memory.

## Project layout

All app files live under `Python BI/MyStreamlit App/`:

```text
MyStreamlit App/
|-- app.py, start_local.py, requirements.txt
|-- modules/       reusable application code
|-- tests/         regression and acceptance tests
|-- scripts/       verification, release, and data-generation commands
|-- assets/        CSS and visual resources
|-- data/          workbook, demos, and sample files
|-- docs/          user and operations guides
|-- manifests/     file integrity manifests
|-- reports/       checked-in report data
`-- .streamlit/    Streamlit configuration
```

## Verify

From the `Python BI/MyStreamlit App` folder, run:

```bash
.venv/bin/python tests/test_workspace_update.py
.venv/bin/python scripts/run_final_gate_tests.py
.venv/bin/python scripts/run_final_acceptance.py --rows 10000
```

On Windows, replace `.venv/bin/python` with `.venv\Scripts\python.exe`. Automated acceptance uses synthetic data. The Streamlit integration test requires loopback access. The older `verify_final_release.py` and its manifest describe a historical package and do not verify later changes.

For more detail, see the [installation guide](Python%20BI/MyStreamlit%20App/README_INSTALL.md) and [operations guides](Python%20BI/MyStreamlit%20App/docs/).
