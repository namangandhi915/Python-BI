"""Verify offline handover utilities are not rendered as a Home widget."""
from pathlib import Path
import ast

ROOT=Path(__file__).resolve().parents[1]

def main():
    source=(ROOT/'app.py').read_text(encoding='utf-8')
    ast.parse(source)
    forbidden=('professor_review_ui', 'render_professor_review_home',
               'Professor review preparation', 'Professor Review Centre')
    for term in forbidden:
        assert term not in source, f"Unwanted website review section: {term}"
    assert '    render_home()' in source
    assert '    render_assurance_home(' in source
    assert '    render_operations_home()' in source
    assert not (ROOT/'professor_review_ui.py').exists(), 'Unused UI module must not be shipped'
    assert (ROOT/'modules'/'professor_review.py').exists(), 'Offline documentation utility must remain'
    print('PASS: No professor-named UI; original Home sections and offline evidence preserved')

if __name__=='__main__':main()
