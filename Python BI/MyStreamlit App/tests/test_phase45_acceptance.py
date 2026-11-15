"""Phase 4/5 acceptance, preserving manual gates and accounting distinctions."""
from assurance_phase45 import run_phase45_checks

def main():
    checks=run_phase45_checks()
    errors=[v for v in checks if v.status=='FAIL']
    if errors:
        raise AssertionError('\n'.join(f'{e.id}: {e.detail}' for e in errors))
    auto=[v for v in checks if v.status=='PASS']
    manual=[v for v in checks if v.status=='MANUAL']
    assert len(auto)>=11 and len(manual)>=4
    assert {c.id for c in checks}.issuperset({'F4-01','F4-02','F4-03','F5-01','F5-03','F6-01','SCALE-UI','DEPLOY'})
    print(f'PASS: {len(auto)} automated acceptance contracts; {len(manual)} manual gates correctly pending')
if __name__=='__main__':main()
