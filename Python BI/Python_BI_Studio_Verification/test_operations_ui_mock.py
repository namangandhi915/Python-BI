from contextlib import nullcontext
try:
    import streamlit  # noqa: F401
except ImportError:
    import sys, types
    sys.modules['streamlit'] = types.SimpleNamespace()
import operations_ui

class Fake:
    def __init__(self): self.calls=[]
    def expander(self,*a,**k):self.calls.append('expander');return nullcontext()
    def caption(self,*a,**k):self.calls.append('caption')
    def columns(self,n):return [self]*n
    def metric(self,*a,**k):self.calls.append('metric')
    def warning(self,*a,**k):self.calls.append('warning')
    def dataframe(self,*a,**k):self.calls.append('dataframe')
    def download_button(self,*a,**k):
        self.calls.append('download')
        assert k['mime']=='application/zip' and len(k['data'])>100


def main():
    prior=operations_ui.st
    fake=Fake()
    try:
        operations_ui.st=fake
        operations_ui.render_operations_home()
        assert fake.calls.count('metric')==3
        assert 'expander' in fake.calls and 'warning' in fake.calls
        assert fake.calls.count('download')==1
    finally: operations_ui.st=prior
    print('PASS: Home release-readiness UI mock, blockers, evidence export')

if __name__=='__main__':main()
