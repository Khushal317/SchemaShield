GET_CUSTOMER_PROFILE = """
SELECT id, full_name, email, phone
FROM schemashield_demo.customers
WHERE id = :customer_id
"""

CREATE_CUSTOMER = """
INSERT INTO schemashield_demo.customers (full_name, email, phone)
VALUES (:full_name, :email, :phone)
RETURNING id
"""


def get_customer_profile(connection, customer_id):
    return connection.execute(
        GET_CUSTOMER_PROFILE,
        {"customer_id": customer_id},
    ).fetchone()


def create_customer(connection, full_name, email, phone):
    return connection.execute(
        CREATE_CUSTOMER,
        {"full_name": full_name, "email": email, "phone": phone},
    ).scalar_one()

