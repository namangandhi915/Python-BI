from final_reliability_checks import run_recovery_checks
r=run_recovery_checks()
assert len(r)>=6
assert all(x['status']=='PASS' for x in r),r
print('PASS: Temporary-only local recovery checks, unsafe uploads, CSV and HTML output')
