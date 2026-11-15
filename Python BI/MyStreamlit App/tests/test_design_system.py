from pathlib import Path
from design_system import masthead_html, PAGES


def main():
    for page in PAGES:
        result = masthead_html(page, 'Example dataset', 20)
        assert '20 RECORDS' in result and 'bi-page-masthead' in result
        assert '<h1' in result and 'aria-label' in result
    malicious = '<script>alert("bad")</script>&'
    html = masthead_html('Dashboard', malicious, 500_000)
    assert '<script>' not in html and '&lt;script&gt;' in html
    assert '500,000 RECORDS' in html
    assert malicious not in html
    assert 'NO ACTIVE DATASET' in masthead_html('Home','No active dataset',None)
    style = (Path(__file__).resolve().parents[1] / 'assets' / 'bi_theme.css').read_text(encoding='utf-8')
    required = ('--bi-navy','--bi-blue','--bi-focus','.bi-page-masthead', '.bi-home-hero','.bi-home-grid','prefers-reduced-motion','focus-visible')
    assert all(key in style for key in required)
    assert style.count('{') == style.count('}') and '@import' not in style and 'url(http' not in style
    print('PASS: Four page headers, HTML escaping, responsive design tokens and focus styles')

if __name__=='__main__': main()
