from pathlib import Path
import ast

def main():
    src=(Path(__file__).resolve().parents[1]/'app.py').read_text(encoding='utf-8')
    ast.parse(src)
    for needle in ('from local_file_guard import validate_upload, safe_stored_path',
                   'save_active_dataset(uploaded_file)',
                   'render_explorer_workspace(df)', 'render_executive_dashboard(',
                   'render_investment_intelligence('):
        assert needle in src,needle
    assert src.count('validate_upload(uploaded_file)') >= 2
    assert 'validate_upload(library_upload)' in src
    for marker in ('restore_active_dataset():','delete_saved_dataset(stored_name):'):
        assert marker in src
    assert 'st.login(' not in src
    assert 'professor_review_ui' not in src
    assert 'render_professor_review_home' not in src
    print('PASS: Upload guards installed; no review section added to existing website')
if __name__=='__main__':main()
