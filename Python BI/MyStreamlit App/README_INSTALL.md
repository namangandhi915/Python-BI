# Install, run, and close Python BI Studio

The app has one Streamlit entry point, `app.py`. Supporting code is in `modules/`; automated tests are in `tests/`; command-line tools are in `scripts/`; sample data is in `data/`; and CSS is in `assets/`.

The [GitHub repository](https://github.com/namangandhi915/Python-BI) shares the source code. It is not a hosted website. Each user clones the repository and runs the app locally; the browser address is `http://127.0.0.1:8501` on that same computer.

## First-time setup on Windows

Install Git and Python 3.13. In PowerShell, run:

```powershell
git clone https://github.com/namangandhi915/Python-BI.git
cd Python-BI
cd "Python BI\MyStreamlit App"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe start_local.py
```

## First-time setup on macOS or Linux

Install Git and Python 3.13. In Terminal, run:

```bash
git clone https://github.com/namangandhi915/Python-BI.git
cd Python-BI/"Python BI/MyStreamlit App"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python start_local.py
```

Open `http://127.0.0.1:8501` in a browser. Leave the terminal running while using the app. The launcher listens on the local computer only and does not publish the app to the internet.

## Start and stop it later

After setup, open a terminal in `Python BI/MyStreamlit App` and run:

- Windows: `.venv\Scripts\python.exe start_local.py`
- macOS/Linux: `.venv/bin/python start_local.py`

Press **Ctrl+C** in that terminal to stop the app. Closing the browser tab does not stop the Streamlit process. Run the start command again to use the app later; do not recreate the environment or reinstall packages unless dependencies changed.

The repository contains the sample workbook and synthetic demo files. Uploaded and saved user datasets stay on that user's computer in `stored_datasets/`; they are not included in the GitHub repository.

## Automated checks

From `Python BI/MyStreamlit App`:

```bash
.venv/bin/python scripts/verify_final_release.py
.venv/bin/python scripts/run_final_gate_tests.py
.venv/bin/python scripts/run_final_acceptance.py --rows 10000
```

On Windows, use `.venv\Scripts\python.exe` in place of `.venv/bin/python`. These checks use synthetic data. Browser checks are documented in `docs/05_GATE_BROWSER_CHECKLIST.md`.
