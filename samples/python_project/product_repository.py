LIST_AVAILABLE_PRODUCTS = """
SELECT id, name, price, stock_count
FROM schemashield_demo.products
WHERE stock_count > 0
ORDER BY name
"""


def list_available_products(connection):
    return connection.execute(LIST_AVAILABLE_PRODUCTS).fetchall()

