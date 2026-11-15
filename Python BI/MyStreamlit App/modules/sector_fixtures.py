"""Deterministic fictional sector datasets — never real company records."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd

@dataclass(frozen=True)
class SectorFixture:
    name: str
    frame: pd.DataFrame
    revenue: str
    cost: str
    discount: str
    returns: str
    operating: str
    taxes: str
    category: str
    date: str = 'Date'


def make_sector_fixture(sector: str, rows: int = 120) -> SectorFixture:
    if sector not in ('Retail', 'Services', 'Manufacturing'):
        raise ValueError('Choose Retail, Services or Manufacturing.')
    if not isinstance(rows, int) or not 12 <= rows <= 100_000:
        raise ValueError('Rows must be between 12 and 100,000.')
    n = np.arange(rows)
    dates = pd.Timestamp('2026-01-01') + pd.to_timedelta(n % 180, unit='D')
    if sector == 'Retail':
        category, values = 'ProductCategory', np.take(['Computing','Accessories','Displays'], n % 3)
        revenue, cost, discount, returned, opex, tax = 'GrossSales','CostOfGoods','Discounts','Returns','StoreExpenses','TaxExpense'
        gross = (100 + (n % 7) * 23).astype(float)
        cogs = (55 + (n % 11) * 9).astype(float)
        disc, ret = (n % 4).astype(float), (n % 9 == 0).astype(float) * 12
        expenses = np.full(rows, 6.0)
        taxes = np.full(rows, 3.0)
    elif sector == 'Services':
        category, values = 'ServiceLine', np.take(['Support','Analytics','Consulting'], n % 3)
        revenue, cost, discount, returned, opex, tax = 'ServiceFees','DeliveryCosts','ClientCredits','Refunds','OfficeExpenses','TaxesPaid'
        gross = (200 + (n % 8) * 20).astype(float)
        cogs = (60 + (n % 9) * 8).astype(float)
        disc, ret = (n % 5).astype(float), np.zeros(rows)
        expenses = np.full(rows, 15.0)
        taxes = np.full(rows, 7.0)
    else:
        category, values = 'ProductionLine', np.take(['Components','Hardware','Assemblies'], n % 3)
        revenue, cost, discount, returned, opex, tax = 'InvoiceValue','ProductionCost','TradeDiscount','RejectedReturns','FactoryExpenses','BusinessTax'
        gross = (350 + (n % 9) * 30).astype(float)
        cogs = (225 + (n % 10) * 25).astype(float)
        disc, ret = (n % 3).astype(float) * 4, (n % 19 == 0).astype(float) * 20
        expenses = np.full(rows, 22.0)
        taxes = np.full(rows, 11.0)
    df = pd.DataFrame({'RecordID': [f'FAKE-{sector[:3].upper()}-{i:06d}' for i in n],
                       'Date': dates, category: values, revenue: gross, cost: cogs,
                       discount: disc, returned: ret, opex: expenses, tax: taxes})
    return SectorFixture(sector, df, revenue, cost, discount, returned, opex, tax, category)


def write_demo_csvs(folder, rows: int = 120) -> list[str]:
    from pathlib import Path
    target = Path(folder)
    target.mkdir(parents=True, exist_ok=True)
    filenames=[]
    for sector in ('Retail','Services','Manufacturing'):
        item = make_sector_fixture(sector, rows)
        path = target / f'FAKE_{sector.lower()}_{rows}.csv'
        item.frame.to_csv(path,index=False)
        filenames.append(str(path))
    return filenames
