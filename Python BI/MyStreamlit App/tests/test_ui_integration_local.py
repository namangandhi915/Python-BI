"""Optional offline smoke-check for the new Streamlit controls (no browser)."""
import sys
from contextlib import nullcontext
from types import SimpleNamespace
import pandas as pd
import numpy as np

class FakeSt:
    session_state = {}
    clicked = True
    downloads = []
    outputs = []
    def fragment(self, fn): return fn
    def expander(self,*a,**kw): return nullcontext()
    def columns(self,n,*a,**kw): return [self for _ in range(n)]
    def number_input(self,label,*a,**kwargs): return kwargs.get('value',0)
    def selectbox(self,label,values,*a,**kwargs): return values[kwargs.get('index',0)]
    def caption(self,*a,**kw): pass
    def warning(self,*a,**kw): pass
    def info(self,*a,**kw): pass
    def markdown(self,*a,**kw): pass
    def error(self,*a,**kw): raise AssertionError(str(a))
    def dataframe(self,*a,**kw): self.outputs.append('dataframe')
    def metric(self,*a,**kw): self.outputs.append('metric')
    def line_chart(self,*a,**kw): self.outputs.append('chart')
    def download_button(self,label,*a,**kw): self.downloads.append(label)
    def button(self,*a,**kw): return self.clicked

fake=FakeSt()
sys.modules['streamlit']=fake
from forecast_panel import render_business_stress_test, render_market_research
render_business_stress_test(100,[110],10)
assert len(fake.downloads)==2
frame=pd.DataFrame({'Date':pd.bdate_range('2026-01-01',periods=100), 'Price':100*np.cumprod(np.full(100,1.001))})
render_market_research(frame,'Daily',True)
assert len(fake.downloads)==5 and 'chart' in fake.outputs
fake.clicked=False
render_market_research(frame,'Daily',True)
assert len(fake.downloads)==8
print('PASS: mocked UI stress + simulation + persistent download controls')
