from pathlib import Path
import ast


def main():
    root=Path(__file__).resolve().parents[1]
    app=(root/'app.py').read_text(encoding='utf-8')
    tree=ast.parse(app)
    assert 'from design_system import render_page_masthead' in app
    assert 'from operations_ui import render_operations_home' in app
    assert 'render_page_masthead(' in app
    assert 'if page == "Home":\n    render_home()' in app
    assert 'render_assurance_home(df)' in app
    assert 'public deployment requires authentication' in app
    for required in ('def save_active_dataset','def restore_active_dataset','def delete_saved_dataset',
                     'render_explorer_workspace(df)','render_executive_dashboard(',
                     'render_investment_intelligence(','render_commercial_intelligence(current_data)',
                     'render_planning_workspace(current_data)'):
        assert required in app, required
    for module in ('executive_dashboard.py','investment_workspace.py','full_dataset_engine.py',
                   'commerce_engine.py','report_engine.py','explorer_workspace.py'):
        ast.parse((root/'modules'/module).read_text(encoding='utf-8'))
    print('PASS: Existing data persistence, Dashboards, investment and reports preserved')

if __name__=='__main__':main()
