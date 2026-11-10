LIST_CUSTOMER_ORDERS = """
SELECT id, customer_id, order_total, status, created_at
FROM schemashield_demo.orders
WHERE customer_id = :customer_id
ORDER BY created_at DESC
"""

MARK_ORDER_COMPLETE = """
UPDATE schemashield_demo.orders
SET status = 'complete'
WHERE id = :order_id
"""


def list_customer_orders(connection, customer_id):
    return connection.execute(
        LIST_CUSTOMER_ORDERS,
        {"customer_id": customer_id},
    ).fetchall()


def mark_order_complete(connection, order_id):
    connection.execute(MARK_ORDER_COMPLETE, {"order_id": order_id})

