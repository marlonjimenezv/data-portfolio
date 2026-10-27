-- Business questions answered with SQL (SQLite) on the cleaned Online Retail II data.
-- Tables: invoices, invoice_lines, products, customers (see sql/schema.sql).
-- Fiscal year (FY) = 12 months from December to November.
-- Each query starts with a "-- Q<n>:" line; src/sql_bonus.py runs them in order.

-- Q1: How do net revenue, orders and average order value move month by month?
SELECT i.month,
       ROUND(SUM(l.line_revenue), 2)                                        AS net_revenue,
       COUNT(DISTINCT CASE WHEN i.type = 'Sale' THEN i.invoice_no END)      AS orders,
       ROUND(SUM(CASE WHEN i.type = 'Sale' THEN l.line_revenue END)
             / COUNT(DISTINCT CASE WHEN i.type = 'Sale' THEN i.invoice_no END), 2) AS avg_order_value
FROM invoices i
JOIN invoice_lines l ON l.invoice_no = i.invoice_no
GROUP BY i.month
ORDER BY i.month;

-- Q2: Month-over-month growth of net revenue (window function LAG).
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

-- Q3: Fiscal-year totals and year-over-year change.
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

-- Q4: Top 10 products by net revenue in FY2011.
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

-- Q5: Which markets matter most? The UK plus the top 10 international markets in FY2011.
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

-- Q6: How concentrated is revenue? Share of FY2011 revenue by customer decile (NTILE).
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

-- Q7: Customer segments by number of orders in FY2011.
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

-- Q8: Did FY2010 customers come back in FY2011? (retention)
WITH fy10 AS (SELECT DISTINCT customer_id FROM invoices
              WHERE type = 'Sale' AND customer_id IS NOT NULL AND month BETWEEN '2009-12' AND '2010-11'),
     fy11 AS (SELECT DISTINCT customer_id FROM invoices
              WHERE type = 'Sale' AND customer_id IS NOT NULL AND month BETWEEN '2010-12' AND '2011-11')
SELECT (SELECT COUNT(*) FROM fy10)                                       AS customers_fy2010,
       (SELECT COUNT(*) FROM fy10 WHERE customer_id IN (SELECT customer_id FROM fy11)) AS also_bought_fy2011,
       ROUND(100.0 * (SELECT COUNT(*) FROM fy10 WHERE customer_id IN (SELECT customer_id FROM fy11))
             / (SELECT COUNT(*) FROM fy10), 1)                           AS retention_pct,
       (SELECT COUNT(*) FROM fy11 WHERE customer_id NOT IN (SELECT customer_id FROM fy10)) AS new_in_fy2011;

-- Q9: Products with the highest return rate in FY2011 (minimum GBP 5,000 of sales).
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

-- Q10: When do orders arrive? Orders and revenue by weekday (FY2011; the shop records no Saturday orders).
SELECT CASE strftime('%w', i.invoice_date)
         WHEN '0' THEN '7 Sun' WHEN '1' THEN '1 Mon' WHEN '2' THEN '2 Tue' WHEN '3' THEN '3 Wed'
         WHEN '4' THEN '4 Thu' WHEN '5' THEN '5 Fri' ELSE '6 Sat' END     AS weekday,
       COUNT(DISTINCT i.invoice_no)                                       AS orders,
       ROUND(SUM(l.line_revenue), 2)                                      AS gross_sales
FROM invoices i JOIN invoice_lines l ON l.invoice_no = i.invoice_no
WHERE i.type = 'Sale' AND i.month BETWEEN '2010-12' AND '2011-11'
GROUP BY weekday
ORDER BY weekday;

-- Q11: Basket size: lines and units per order, by customer type (FY2011).
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

-- Q12: Top 10 customers by FY2011 revenue, with orders and days since their last order.
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

-- Q13: Which products are bought together most often? (top 50 products, FY2011)
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
