"""Check cross-module benchmark on modest data; bigger tests opt-in."""
from assurance_performance import benchmark_workflow

def main():
    results=benchmark_workflow(1000)
    assert results['rows']==1000 and results['columns']==14
    assert results['sentinel_found_once'] and results['financial_reconciled']
    assert results['category_reconciled'] and results['period_reconciled']
    assert results['full_app_certified'] is False
    assert set(results['timings_seconds']).issuperset({'search_all_columns_seconds','mapped_finance_seconds','category_reconciliation_seconds'})
    try: benchmark_workflow(500001)
    except ValueError:pass
    else:raise AssertionError('Row safety limit not enforced')
    print('PASS: Real module pipeline, matching records, reconciliation and benchmark bounds')
if __name__=='__main__':main()
