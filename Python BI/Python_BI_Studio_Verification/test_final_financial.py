from final_financial_checks import financial_edge_suite
r=financial_edge_suite()
assert len(r)>=20
failed=[x for x in r if x['status']!='PASS']
assert not failed,failed
print(f'PASS: {len(r)} independent financial, dashboard, report and sector checks')
