# Accounting definitions and financial verification rules

**Always check the real meaning of source columns.** Synthetic fixtures have explicit field definitions. Do not treat a generic column labelled `Sales` as gross revenue if it is already net of returns or discounts. Never add costs already included in another mapped expense.

| Fixture | Revenue | Cost of sales | Discounts | Returns | Operating expenses | Tax |
|---|---|---|---|---|---|---|
| Retail | `GrossSales` | `CostOfGoods` | `Discounts` | `Returns` | `StoreExpenses` | `TaxExpense` |
| Services | `ServiceFees` | `DeliveryCosts` | `ClientCredits` | `Refunds` | `OfficeExpenses` | `TaxesPaid` |
| Manufacturing | `InvoiceValue` | `ProductionCost` | `TradeDiscount` | `RejectedReturns` | `FactoryExpenses` | `BusinessTax` |

Formulas used by commercial metrics:

- Gross Revenue = sum of the chosen revenue column, **before** separately mapped discounts/returns.
- Net Revenue = Gross Revenue − Discounts − Returns.
- Mapped Costs = Cost of Sales + Operating Expenses + Taxes **only when cost of sales is mapped**.
- Profit After Mapped Costs = Net Revenue − Mapped Costs; this is **not necessarily accounting net profit**.
- Net Business Loss = maximum of (−total mapped profit, 0). Sum of losses on loss-making individual records can differ.
- Profit Margin (%) = Profit After Mapped Costs / Net Revenue × 100; undefined when net revenue is zero.
- Net Profit display requires an explicit confirmation that relevant expense/tax fields are complete. In real accounting, additional items such as financing costs, depreciation, amortisation and other income/expenses may matter.
- ROI is available only when total invested capital is positive and the user has affirmed it is **additive per row**, not a repeated portfolio/account balance.
- Dates with invalid values are excluded from time trends but not business total KPIs.

**Limitations:** No currency conversion, no accrual accounting validation, no automated tax reconciliation and no live financial feeds. Independent bookkeeping/professor review remains a manual gate.
