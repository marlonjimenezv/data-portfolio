# SQL results: business questions on the Online Retail II data

Sample project built with public data (Online Retail II, UCI ML Repository, CC BY 4.0).
Database: SQLite, built by `src/sql_bonus.py` from the cleaned data. Queries: `sql/queries.sql`.
FY2011 = December 2010 to November 2011. Amounts in GBP.

## Q1: How do net revenue, orders and average order value move month by month?

```sql
SELECT i.month,
       ROUND(SUM(l.line_revenue), 2)                                        AS net_revenue,
       COUNT(DISTINCT CASE WHEN i.type = 'Sale' THEN i.invoice_no END)      AS orders,
       ROUND(SUM(CASE WHEN i.type = 'Sale' THEN l.line_revenue END)
             / COUNT(DISTINCT CASE WHEN i.type = 'Sale' THEN i.invoice_no END), 2) AS avg_order_value
FROM invoices i
JOIN invoice_lines l ON l.invoice_no = i.invoice_no
GROUP BY i.month
ORDER BY i.month;
```

| month | net_revenue | orders | avg_order_value |
|---|---|---|---|
| 2009-12 | 778,343.08 | 1,666 | 478.93 |
| 2010-01 | 604,831.79 | 1,049 | 583.70 |
| 2010-02 | 525,334.23 | 1,189 | 452.41 |
| 2010-03 | 752,102.13 | 1,647 | 462.48 |
| 2010-04 | 636,315.67 | 1,435 | 450.41 |
| 2010-05 | 606,299.14 | 1,484 | 433.62 |
| 2010-06 | 670,246.33 | 1,612 | 432.12 |
| 2010-07 | 615,861.59 | 1,507 | 420.04 |
| 2010-08 | 661,640.12 | 1,402 | 480.77 |
| 2010-09 | 841,556.70 | 1,789 | 485.88 |
| 2010-10 | 1,068,984.91 | 2,244 | 487.72 |
| 2010-11 | 1,394,601.80 | 2,719 | 525.82 |
| 2010-12 | 758,090.50 | 1,550 | 500.41 |
| 2011-01 | 578,855.19 | 1,081 | 620.15 |
| 2011-02 | 499,464.35 | 1,093 | 464.59 |
| 2011-03 | 679,329.21 | 1,440 | 479.05 |
| 2011-04 | 482,061.93 | 1,235 | 417.31 |
| 2011-05 | 731,004.77 | 1,668 | 443.62 |
| 2011-06 | 723,845.14 | 1,525 | 483.65 |
| 2011-07 | 676,812.08 | 1,452 | 473.98 |
| 2011-08 | 701,289.93 | 1,339 | 540.86 |
| 2011-09 | 1,011,339.74 | 1,818 | 565.63 |
| 2011-10 | 1,061,701.22 | 2,005 | 550.28 |
| 2011-11 | 1,427,124.54 | 2,751 | 527.85 |

## Q2: Month-over-month growth of net revenue (window function LAG).

```sql
WITH m AS (
  SELECT i.month, SUM(l.line_revenue) AS net_revenue
  FROM invoices i JOIN invoice_lines l ON l.invoice_no = i.invoice_no
  GROUP BY i.month
)
SELECT month,
       ROUND(net_revenue, 2) AS net_revenue,
       ROUND(100.0 * (net_revenue / LAG(net_revenue) OVER (ORDER BY month) - 1), 1) AS mom_growth_pct
FROM m
ORDER BY month;
```

| month | net_revenue | mom_growth_pct |
|---|---|---|
| 2009-12 | 778,343.08 |  |
| 2010-01 | 604,831.79 | -22.30 |
| 2010-02 | 525,334.23 | -13.10 |
| 2010-03 | 752,102.13 | 43.20 |
| 2010-04 | 636,315.67 | -15.40 |
| 2010-05 | 606,299.14 | -4.70 |
| 2010-06 | 670,246.33 | 10.50 |
| 2010-07 | 615,861.59 | -8.10 |
| 2010-08 | 661,640.12 | 7.40 |
| 2010-09 | 841,556.70 | 27.20 |
| 2010-10 | 1,068,984.91 | 27.00 |
| 2010-11 | 1,394,601.80 | 30.50 |
| 2010-12 | 758,090.50 | -45.60 |
| 2011-01 | 578,855.19 | -23.60 |
| 2011-02 | 499,464.35 | -13.70 |
| 2011-03 | 679,329.21 | 36.00 |
| 2011-04 | 482,061.93 | -29.00 |
| 2011-05 | 731,004.77 | 51.60 |
| 2011-06 | 723,845.14 | -1.00 |
| 2011-07 | 676,812.08 | -6.50 |
| 2011-08 | 701,289.93 | 3.60 |
| 2011-09 | 1,011,339.74 | 44.20 |
| 2011-10 | 1,061,701.22 | 5.00 |
| 2011-11 | 1,427,124.54 | 34.40 |

## Q3: Fiscal-year totals and year-over-year change.

```sql
WITH fy AS (
  SELECT CASE WHEN i.month >= '2010-12' THEN 'FY2011 (Dec 2010 - Nov 2011)'
              ELSE 'FY2010 (Dec 2009 - Nov 2010)' END AS fiscal_year,
         i.invoice_no, i.type, i.customer_id, l.line_revenue
  FROM invoices i JOIN invoice_lines l ON l.invoice_no = i.invoice_no
)
SELECT fiscal_year,
       ROUND(SUM(line_revenue), 2)                                         AS net_revenue,
       COUNT(DISTINCT CASE WHEN type = 'Sale' THEN invoice_no END)         AS orders,
       COUNT(DISTINCT customer_id)                                         AS identified_customers
FROM fy
GROUP BY fiscal_year
ORDER BY fiscal_year;
```

| fiscal_year | net_revenue | orders | identified_customers |
|---|---|---|---|
| FY2010 (Dec 2009 - Nov 2010) | 9,156,117.49 | 19,743 | 4,267 |
| FY2011 (Dec 2010 - Nov 2011) | 9,330,918.60 | 18,957 | 4,321 |

## Q4: Top 10 products by net revenue in FY2011.

```sql
SELECT p.stock_code, p.description,
       SUM(l.quantity)                 AS units,
       ROUND(SUM(l.line_revenue), 2)   AS net_revenue
FROM invoice_lines l
JOIN invoices i ON i.invoice_no = l.invoice_no
JOIN products p ON p.stock_code = l.stock_code
WHERE i.month BETWEEN '2010-12' AND '2011-11'
GROUP BY p.stock_code, p.description
ORDER BY net_revenue DESC
LIMIT 10;
```

| stock_code | description | units | net_revenue |
|---|---|---|---|
| 22423 | REGENCY CAKESTAND 3 TIER | 12,556 | 158,569.32 |
| 85123A | WHITE HANGING HEART T-LIGHT HOLDER | 34,517 | 97,408.35 |
| 47566 | PARTY BUNTING | 17,870 | 97,325.40 |
| 85099B | JUMBO BAG RED RETROSPOT | 46,166 | 89,980.09 |
| 23084 | RABBIT NIGHT LIGHT | 26,340 | 57,058.18 |
| 22086 | PAPER CHAIN KIT 50'S CHRISTMAS | 16,788 | 56,847.48 |
| 84879 | ASSORTED COLOUR BIRD ORNAMENT | 34,952 | 56,629.68 |
| 79321 | CHILLI LIGHTS | 9,761 | 51,112.67 |
| 22502 | PICNIC BASKET WICKER SMALL | 1,862 | 51,023.52 |
| 22197 | SMALL POPCORN HOLDER | 50,229 | 45,558.06 |

## Q5: Which markets matter most? The UK plus the top 10 international markets in FY2011.

```sql
WITH c AS (
  SELECT i.country, SUM(l.line_revenue) AS net_revenue
  FROM invoices i JOIN invoice_lines l ON l.invoice_no = i.invoice_no
  WHERE i.month BETWEEN '2010-12' AND '2011-11'
  GROUP BY i.country
)
SELECT country,
       ROUND(net_revenue, 2)                                         AS net_revenue,
       ROUND(100.0 * net_revenue / SUM(net_revenue) OVER (), 2)      AS share_of_total_pct
FROM c
ORDER BY net_revenue DESC
LIMIT 11;
```

| country | net_revenue | share_of_total_pct |
|---|---|---|
| United Kingdom | 7,883,043.82 | 84.48 |
| Netherlands | 271,751.52 | 2.91 |
| EIRE | 252,256.98 | 2.70 |
| Germany | 193,774.96 | 2.08 |
| France | 175,685.33 | 1.88 |
| Australia | 136,922.50 | 1.47 |
| Switzerland | 52,483.05 | 0.56 |
| Spain | 51,503.22 | 0.55 |
| Japan | 35,536.72 | 0.38 |
| Belgium | 35,382.53 | 0.38 |
| Sweden | 35,166.41 | 0.38 |

## Q6: How concentrated is revenue? Share of FY2011 revenue by customer decile (NTILE).

```sql
WITH cust AS (
  SELECT i.customer_id, SUM(l.line_revenue) AS revenue
  FROM invoices i JOIN invoice_lines l ON l.invoice_no = i.invoice_no
  WHERE i.customer_id IS NOT NULL AND i.month BETWEEN '2010-12' AND '2011-11'
  GROUP BY i.customer_id
), ranked AS (
  SELECT customer_id, revenue, NTILE(10) OVER (ORDER BY revenue DESC) AS decile
  FROM cust
)
SELECT decile,
       COUNT(*)                                                        AS customers,
       ROUND(SUM(revenue), 2)                                          AS revenue,
       ROUND(100.0 * SUM(revenue) / (SELECT SUM(revenue) FROM cust), 1) AS share_pct
FROM ranked
GROUP BY decile
ORDER BY decile;
```

| decile | customers | revenue | share_pct |
|---|---|---|---|
| 1 | 433 | 4,773,940.24 | 60.20 |
| 2 | 432 | 1,082,093.11 | 13.70 |
| 3 | 432 | 666,194.49 | 8.40 |
| 4 | 432 | 452,847.16 | 5.70 |
| 5 | 432 | 317,531.06 | 4.00 |
| 6 | 432 | 232,294.76 | 2.90 |
| 7 | 432 | 165,705.91 | 2.10 |
| 8 | 432 | 122,698.17 | 1.50 |
| 9 | 432 | 79,914.60 | 1.00 |
| 10 | 432 | 34,105.41 | 0.40 |

## Q7: Customer segments by number of orders in FY2011.

```sql
WITH freq AS (
  SELECT customer_id, COUNT(DISTINCT invoice_no) AS orders
  FROM invoices
  WHERE type = 'Sale' AND customer_id IS NOT NULL AND month BETWEEN '2010-12' AND '2011-11'
  GROUP BY customer_id
)
SELECT CASE WHEN orders = 1 THEN '1 order'
            WHEN orders BETWEEN 2 AND 4 THEN '2-4 orders'
            WHEN orders BETWEEN 5 AND 9 THEN '5-9 orders'
            ELSE '10+ orders' END                                      AS segment,
       COUNT(*)                                                        AS customers,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM freq), 1)        AS share_of_customers_pct
FROM freq
GROUP BY segment
ORDER BY MIN(orders);
```

| segment | customers | share_of_customers_pct |
|---|---|---|
| 1 order | 1,551 | 36.10 |
| 2-4 orders | 1,696 | 39.50 |
| 5-9 orders | 683 | 15.90 |
| 10+ orders | 363 | 8.50 |

## Q8: Did FY2010 customers come back in FY2011? (retention)

```sql
WITH fy10 AS (SELECT DISTINCT customer_id FROM invoices
              WHERE type = 'Sale' AND customer_id IS NOT NULL AND month BETWEEN '2009-12' AND '2010-11'),
     fy11 AS (SELECT DISTINCT customer_id FROM invoices
              WHERE type = 'Sale' AND customer_id IS NOT NULL AND month BETWEEN '2010-12' AND '2011-11')
SELECT (SELECT COUNT(*) FROM fy10)                                       AS customers_fy2010,
       (SELECT COUNT(*) FROM fy10 WHERE customer_id IN (SELECT customer_id FROM fy11)) AS also_bought_fy2011,
       ROUND(100.0 * (SELECT COUNT(*) FROM fy10 WHERE customer_id IN (SELECT customer_id FROM fy11))
             / (SELECT COUNT(*) FROM fy10), 1)                           AS retention_pct,
       (SELECT COUNT(*) FROM fy11 WHERE customer_id NOT IN (SELECT customer_id FROM fy10)) AS new_in_fy2011;
```

| customers_fy2010 | also_bought_fy2011 | retention_pct | new_in_fy2011 |
|---|---|---|---|
| 4,239 | 2,708 | 63.90 | 1,585 |

## Q9: Products with the highest return rate in FY2011 (minimum GBP 5,000 of sales).

```sql
WITH p AS (
  SELECT l.stock_code,
         SUM(CASE WHEN i.type = 'Sale'   THEN l.line_revenue ELSE 0 END)  AS sales,
         -SUM(CASE WHEN i.type = 'Return' THEN l.line_revenue ELSE 0 END) AS returns
  FROM invoice_lines l JOIN invoices i ON i.invoice_no = l.invoice_no
  WHERE i.month BETWEEN '2010-12' AND '2011-11'
  GROUP BY l.stock_code
)
SELECT p.stock_code, pr.description,
       ROUND(sales, 2)                    AS sales,
       ROUND(returns, 2)                  AS returns,
       ROUND(100.0 * returns / sales, 1)  AS return_rate_pct
FROM p JOIN products pr ON pr.stock_code = p.stock_code
WHERE sales >= 5000
ORDER BY return_rate_pct DESC
LIMIT 10;
```

| stock_code | description | sales | returns | return_rate_pct |
|---|---|---|---|---|
| 23166 | MEDIUM CERAMIC TOP STORAGE JAR | 81,448.21 | 77,479.64 | 95.10 |
| 23113 | PANTRY CHOPPING BOARD | 5,806.43 | 4,803.06 | 82.70 |
| 21108 | FAIRY CAKE FLANNEL ASSORTED COLOUR | 17,835.86 | 6,553.62 | 36.70 |
| 22273 | FELTCRAFT DOLL MOLLY | 11,789.85 | 3,509.70 | 29.80 |
| 47566B | TEA TIME PARTY BUNTING | 12,921.47 | 3,692.95 | 28.60 |
| 22191 | IVORY DINER WALL CLOCK | 11,657.39 | 2,653.70 | 22.80 |
| 22655 | VINTAGE RED KITCHEN CABINET | 8,125.00 | 1,730.50 | 21.30 |
| 48185 | DOORMAT FAIRY CAKE | 23,765.66 | 4,554.90 | 19.20 |
| 71477 | COLOUR GLASS. STAR T-LIGHT HOLDER | 19,022.42 | 3,336.97 | 17.50 |
| 22838 | 3 TIER CAKE TIN RED AND CREAM | 9,573.68 | 1,656.65 | 17.30 |

## Q10: When do orders arrive? Orders and revenue by weekday (FY2011; the shop records no Saturday orders).

```sql
SELECT CASE strftime('%w', i.invoice_date)
         WHEN '0' THEN '7 Sun' WHEN '1' THEN '1 Mon' WHEN '2' THEN '2 Tue' WHEN '3' THEN '3 Wed'
         WHEN '4' THEN '4 Thu' WHEN '5' THEN '5 Fri' ELSE '6 Sat' END     AS weekday,
       COUNT(DISTINCT i.invoice_no)                                       AS orders,
       ROUND(SUM(l.line_revenue), 2)                                      AS gross_sales
FROM invoices i JOIN invoice_lines l ON l.invoice_no = i.invoice_no
WHERE i.type = 'Sale' AND i.month BETWEEN '2010-12' AND '2011-11'
GROUP BY weekday
ORDER BY weekday;
```

| weekday | orders | gross_sales |
|---|---|---|
| 1 Mon | 2,950 | 1,602,849.29 |
| 2 Tue | 3,395 | 2,029,758.01 |
| 3 Wed | 3,562 | 1,709,549.25 |
| 4 Thu | 3,968 | 2,003,428.37 |
| 5 Fri | 2,945 | 1,513,075.45 |
| 7 Sun | 2,137 | 774,068.03 |

## Q11: Basket size: lines and units per order, by customer type (FY2011).

```sql
WITH b AS (
  SELECT i.invoice_no,
         CASE WHEN i.customer_id IS NULL THEN 'Guest' ELSE 'Identified customer' END AS customer_type,
         COUNT(*) AS lines, SUM(l.quantity) AS units, SUM(l.line_revenue) AS value
  FROM invoices i JOIN invoice_lines l ON l.invoice_no = i.invoice_no
  WHERE i.type = 'Sale' AND i.month BETWEEN '2010-12' AND '2011-11'
  GROUP BY i.invoice_no, customer_type
)
SELECT customer_type,
       COUNT(*)              AS orders,
       ROUND(AVG(lines), 1)  AS avg_lines,
       ROUND(AVG(units), 1)  AS avg_units,
       ROUND(AVG(value), 2)  AS avg_order_value
FROM b
GROUP BY customer_type;
```

| customer_type | orders | avg_lines | avg_units | avg_order_value |
|---|---|---|---|---|
| Guest | 1,331 | 92.90 | 295.10 | 1,057.65 |
| Identified customer | 17,626 | 21.20 | 275.50 | 466.64 |

## Q12: Top 10 customers by FY2011 revenue, with orders and days since their last order.

```sql
SELECT i.customer_id,
       c.country,
       COUNT(DISTINCT CASE WHEN i.type = 'Sale' THEN i.invoice_no END)  AS orders,
       ROUND(SUM(l.line_revenue), 2)                                    AS net_revenue,
       CAST(julianday('2011-11-30') - julianday(MAX(i.invoice_date)) AS INTEGER) AS days_since_last_order
FROM invoices i
JOIN invoice_lines l ON l.invoice_no = i.invoice_no
JOIN customers c ON c.customer_id = i.customer_id
WHERE i.month BETWEEN '2010-12' AND '2011-11'
GROUP BY i.customer_id, c.country
ORDER BY net_revenue DESC
LIMIT 10;
```

| customer_id | country | orders | net_revenue | days_since_last_order |
|---|---|---|---|---|
| 14646 | Netherlands | 69 | 267,050.00 | 6 |
| 18102 | United Kingdom | 57 | 248,171.76 | 1 |
| 17450 | United Kingdom | 45 | 188,013.13 | 0 |
| 12415 | Australia | 20 | 123,638.18 | 14 |
| 14911 | EIRE | 189 | 121,941.87 | 0 |
| 14156 | EIRE | 54 | 113,685.77 | 0 |
| 17511 | United Kingdom | 29 | 80,758.88 | 6 |
| 16684 | United Kingdom | 27 | 60,518.14 | 1 |
| 16029 | United Kingdom | 62 | 60,369.93 | 28 |
| 13694 | United Kingdom | 47 | 59,830.38 | 15 |

## Q13: Which products are bought together most often? (top 50 products, FY2011)

```sql
WITH top_products AS (
  SELECT l.stock_code
  FROM invoice_lines l JOIN invoices i ON i.invoice_no = l.invoice_no
  WHERE i.type = 'Sale' AND i.month BETWEEN '2010-12' AND '2011-11'
  GROUP BY l.stock_code
  ORDER BY COUNT(DISTINCT l.invoice_no) DESC
  LIMIT 50
), basket AS (
  SELECT DISTINCT l.invoice_no, l.stock_code
  FROM invoice_lines l JOIN invoices i ON i.invoice_no = l.invoice_no
  WHERE i.type = 'Sale' AND i.month BETWEEN '2010-12' AND '2011-11'
    AND l.stock_code IN (SELECT stock_code FROM top_products)
)
SELECT a.stock_code AS product_a, pa.description AS description_a,
       b.stock_code AS product_b, pb.description AS description_b,
       COUNT(*)     AS orders_together
FROM basket a
JOIN basket b ON a.invoice_no = b.invoice_no AND a.stock_code < b.stock_code
JOIN products pa ON pa.stock_code = a.stock_code
JOIN products pb ON pb.stock_code = b.stock_code
GROUP BY a.stock_code, b.stock_code
ORDER BY orders_together DESC
LIMIT 10;
```

| product_a | description_a | product_b | description_b | orders_together |
|---|---|---|---|---|
| 22386 | JUMBO BAG PINK POLKADOT | 85099B | JUMBO BAG RED RETROSPOT | 811 |
| 22697 | GREEN REGENCY TEACUP AND SAUCER | 22699 | ROSES REGENCY TEACUP AND SAUCER | 740 |
| 21931 | JUMBO STORAGE BAG SUKI | 85099B | JUMBO BAG RED RETROSPOT | 700 |
| 22411 | JUMBO SHOPPER VINTAGE RED PAISLEY | 85099B | JUMBO BAG RED RETROSPOT | 659 |
| 20725 | LUNCH BAG RED RETROSPOT | 22383 | LUNCH BAG SUKI  DESIGN | 640 |
| 20725 | LUNCH BAG RED RETROSPOT | 20727 | LUNCH BAG  BLACK SKULL. | 617 |
| 22726 | ALARM CLOCK BAKELIKE GREEN | 22727 | ALARM CLOCK BAKELIKE RED | 596 |
| 20725 | LUNCH BAG RED RETROSPOT | 22384 | LUNCH BAG PINK POLKADOT | 592 |
| 20725 | LUNCH BAG RED RETROSPOT | 85099B | JUMBO BAG RED RETROSPOT | 569 |
| 85099B | JUMBO BAG RED RETROSPOT | 85099C | JUMBO  BAG BAROQUE BLACK WHITE | 567 |
