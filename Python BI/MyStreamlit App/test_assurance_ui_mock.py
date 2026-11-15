"""Lightweight interface wiring test independent of local Streamlit installation."""
from contextlib import nullcontext
import importlib
import pandas as pd
import assurance_ui

class Fake:
    def __init__(self): self.calls=[]
    def expander(self,*a,**k):self.calls.append('expander');return nullcontext()
    def caption(self,*a,**k):self.calls.append('caption')
    def info(self,*a,**k):self.calls.append('info')
    def warning(self,*a,**k):self.calls.append('warning')
    def error(self,*a,**k):raise AssertionError(f'Streamlit error: {a}')
    def selectbox(self,label,options,**k):self.calls.append('selectbox');return options[k.get('index',0)]
    def checkbox(self,*a,**k):self.calls.append('checkbox');return False
    def columns(self,n):return [self]*n
    def metric(self,*a,**k):self.calls.append('metric')
    def dataframe(self,*a,**k):self.calls.append('dataframe')
    def download_button(self,*a,**k):self.calls.append('download')

def main():
    previous=assurance_ui.st
    fake=Fake()
    try:
        assurance_ui.st=fake
        assurance_ui.render_assurance_home(None)
        assert 'info' in fake.calls
        fake.calls=[]
        assurance_ui.render_assurance_home(pd.DataFrame({'Sales':[1.0,2.0], 'Total Cost':[0.4,0.5]}))
        assert fake.calls.count('metric')==4 and fake.calls.count('download')==1
        assert 'dataframe' in fake.calls and 'error' not in fake.calls
    finally:
        assurance_ui.st=previous
    print('PASS: Home assurance controls, scope labels, preview and safe download')
if __name__=='__main__':main()
