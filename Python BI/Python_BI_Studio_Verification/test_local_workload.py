import sys,types
try:import streamlit
except ImportError:sys.modules['streamlit']=types.SimpleNamespace()
from local_workload_benchmark import run_workload

def main():
    result=run_workload(1000)
    assert result['status']=='PASS' and result['rows']==1000
    assert result['includes_html_report_generation']
    assert not result['streamlit_full_ui_certified']
    print('PASS: Source/search/quality/finance/category/charts/report bounded workflow')
if __name__=='__main__':main()
