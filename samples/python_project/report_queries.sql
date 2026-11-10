SELECT
    c.full_name,
    c.email,
    o.order_total,
    o.status
FROM schemashield_demo.customers AS c
JOIN schemashield_demo.orders AS o ON o.customer_id = c.id
ORDER BY o.created_at DESC;

SELECT id, name, price, stock_count
FROM schemashield_demo.products
WHERE stock_count > 0;

