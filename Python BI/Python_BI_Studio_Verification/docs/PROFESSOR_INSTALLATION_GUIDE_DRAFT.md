# Python BI Studio
## Local Installation and User Guide — Draft

### 1. System Requirements

- Windows computer
- Python 3.13.16 (verified development version)
- Visual Studio Code
- Python extension for VS Code
- Modern web browser
- Internet connection for initial dependency installation

### 2. Project Installation

Extract the approved Python BI Studio submission ZIP.

Open the extracted application folder in VS Code.

Open Terminal > New Terminal.

Check Python:

    python --version

Create the virtual environment:

    python -m venv .venv

Activate it in PowerShell:

    .\.venv\Scripts\Activate.ps1

If PowerShell blocks activation, use:

    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    .\.venv\Scripts\Activate.ps1

Install dependencies:

    python -m pip install -r requirements.txt

Check dependency compatibility:

    python -m pip check

### 3. Main Python Dependencies

Verified direct dependencies:

- streamlit==1.66.0
- pandas==3.0.6
- numpy==2.5.4
- plotly==7.1.0
- openpyxl==3.1.5

Python 3.13.16 was used during local verification.

### 4. Launch Python BI Studio

Start the local application:

    python start_local.py

Open:

    http://127.0.0.1:8501

The verification project was also tested separately
on port 8502.

Only one application server is necessary.

Stop Streamlit using Ctrl+C in the VS Code terminal.

### 5. Main Application Modules

- Home: Corporate overview and navigation
- Data Workspace: Exploration and validation
- Commercial Intelligence: Financial calculations
- Dashboard: Charts, KPIs and executive reporting
- Investment Intelligence: Business and market research
- Dataset Library: Local dataset management

### 6. Data and Financial Assumptions

Map revenue, costs, discounts and returns correctly.

Operating expenses and taxes must be considered
when determining accounting net profit.

Profit after mapped costs is not automatically
equivalent to final accounting net profit.

Market analysis and investment simulations
do not guarantee future returns.

### 7. Demonstration Datasets

Use the approved synthetic demonstration datasets
included in the final submission package.

Do not upload confidential company or customer data
during the professor demonstration.

The final package's included datasets must be
confirmed before this guide is approved.

### 8. Automated Verification

Run:

    python verify_final_release.py

Then:

    python run_final_gate_tests.py

The current verification copy previously passed
36 automated regression scripts.

Release checksum verification applies only to
files listed in the release manifest.

Final submission tests must be rerun after packaging.

### 9. Known Limitations

- Intended for local academic evaluation
- Not approved for public multi-user deployment
- User authentication and data isolation are not complete
- The 10,000-row browser test passed
- The 100,000-row browser test remains unresolved
- Large-dataset reliability is not yet certified
- Professor approval remains pending

### 10. Project Status

DRAFT — Final professor-submission package
has not yet been created or approved.
