# DAX measures: education procurement model

Twelve measures for the star schema in `powerbi/data/`. Create them in a measure table called `_Measures`
(Home → Enter data → name it `_Measures` → Load, then add each measure to it).
Expected values for the whole dataset are listed in [`VALORES_ESPERADOS.md`](VALORES_ESPERADOS.md).

Model: `fact_contracts` (one row per contract) related many-to-one to `dim_entity`, `dim_modality`,
`dim_contract_type`, `dim_status` (by their `_key` columns) and to `dim_date` (`fact_contracts[date_signed]` →
`dim_date[date]`, marked as the date table).

---

### 1. Total Contracts
```DAX
Total Contracts = COUNTROWS ( fact_contracts )
```
Counts contracts in the current filter context. Base for every percentage below.

### 2. Total Value
```DAX
Total Value = SUM ( fact_contracts[contract_value] )
```
Sum of contract values in COP. Format as Whole number with thousands separator, or as a custom format
in billions: `#,0.0,,,"bn"`.

### 3. Average Contract Value
```DAX
Average Contract Value = DIVIDE ( [Total Value], [Total Contracts] )
```
`DIVIDE` returns blank instead of an error when there are no contracts.

### 4. Median Contract Value
```DAX
Median Contract Value = MEDIAN ( fact_contracts[contract_value] )
```
Better than the average for skewed data: a few very large contracts pull the average up
(average ≈ COP 114.5M vs median ≈ COP 21.4M).

### 5. Direct Contracting % (contracts)
```DAX
Direct Contracting % (contracts) =
DIVIDE (
    CALCULATE ( [Total Contracts], dim_modality[is_direct] = 1 ),
    [Total Contracts]
)
```
Share of contracts awarded without a competitive process. `CALCULATE` adds the filter
`is_direct = 1` on top of whatever the user has selected in slicers.

### 6. Direct Contracting % (value)
```DAX
Direct Contracting % (value) =
DIVIDE (
    CALCULATE ( [Total Value], dim_modality[is_direct] = 1 ),
    [Total Value]
)
```
Same idea, weighted by money. Comparing 5 and 6 shows that direct awards are many but smaller.

### 7. Individuals % (contracts)
```DAX
Individuals % (contracts) =
DIVIDE (
    CALCULATE ( [Total Contracts], fact_contracts[supplier_type] = "Natural person" ),
    [Total Contracts]
)
```
Share of contracts signed with individual contractors (identified with a personal ID).

### 8. SME Suppliers %
```DAX
SME Suppliers % =
DIVIDE (
    CALCULATE ( [Total Contracts], fact_contracts[is_sme] = 1 ),
    [Total Contracts]
)
```

### 9. Paid % of Value
```DAX
Paid % of Value =
VAR PaidValue = SUM ( fact_contracts[paid_value] )
RETURN
    DIVIDE ( PaidValue, [Total Value] )
```
Payments registered in SECOP II as a share of contract value, at the date the data was extracted.
`VAR` keeps the formula readable and computes the sum once.

### 10. Value YTD
```DAX
Value YTD = TOTALYTD ( [Total Value], dim_date[date] )
```
Running total from January to the month in context. Needs `dim_date` marked as a date table.

### 11. Value MoM %
```DAX
Value MoM % =
VAR CurrentValue = [Total Value]
VAR PreviousValue =
    CALCULATE ( [Total Value], DATEADD ( dim_date[date], -1, MONTH ) )
RETURN
    IF ( NOT ISBLANK ( PreviousValue ), DIVIDE ( CurrentValue - PreviousValue, PreviousValue ) )
```
Month-over-month change. Use it in a table or tooltip by month; blank for January (no previous month in 2025).

### 12. Entity Rank by Value
```DAX
Entity Rank by Value =
IF (
    HASONEVALUE ( dim_entity[entity_name] ),
    RANKX ( ALLSELECTED ( dim_entity[entity_name] ), [Total Value], , DESC, DENSE )
)
```
Ranks entities by contract value within the current slicer selection. Use it as a visual-level filter
(`Entity Rank by Value` ≤ 10) to build a "Top 10 entities" chart that respects the slicers.

---

**Formats.** Percent measures: Percentage, 1 decimal. Value measures: Whole number, thousands separator,
or the custom billions format above. Set formats in Measure tools → Format.
