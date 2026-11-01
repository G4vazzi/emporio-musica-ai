
import csv
from contextlib import closing
from decimal import Decimal, ROUND_HALF_UP

from app.database.connection import (
    DATA_DIR,
    DB_PATH,
    get_connection,
)


SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    category_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    city TEXT
);

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY,
    price_cents INTEGER NOT NULL CHECK (price_cents >= 0),
    name TEXT NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(category_id),
    description TEXT,
    stock_quantity INTEGER NOT NULL CHECK (stock_quantity >= 0),
    status TEXT NOT NULL,
    specs TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    order_date TEXT NOT NULL,
    status TEXT NOT NULL,
    total_cents INTEGER NOT NULL CHECK (total_cents >= 0),
    payment_method TEXT,
    tracking_code TEXT,
    estimated_delivery TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS order_items (
    order_id INTEGER NOT NULL REFERENCES orders(order_id),
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    PRIMARY KEY (order_id, product_id)
);

CREATE TABLE IF NOT EXISTS promotions (
    promotion_id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    discount_percent INTEGER NOT NULL
        CHECK (discount_percent BETWEEN 0 AND 100),
    description TEXT,
    is_active INTEGER NOT NULL
        CHECK (is_active IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_products_category
    ON products(category_id);

CREATE INDEX IF NOT EXISTS idx_orders_customer
    ON orders(customer_id);

CREATE INDEX IF NOT EXISTS idx_promotions_product
    ON promotions(product_id);
"""


def read_rows(filename: str) -> list[dict[str, str]]:
    filepath = DATA_DIR / filename

    if not filepath.is_file():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {filepath}"
        )

    with filepath.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        return list(csv.DictReader(file))


def to_cents(value: str) -> int:
    amount = Decimal(value) * 100

    return int(
        amount.quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP
        )
    )


def optional_text(value: str) -> str | None:
    return value.strip() or None


def import_data() -> None:

    # Leitura dos arquivos CSV
    categories = read_rows("categories.csv")
    customers = read_rows("customers.csv")
    products = read_rows("products.csv")
    orders = read_rows("orders.csv")
    order_items = read_rows("order_items.csv")
    promotions = read_rows("promotions.csv")

    with closing(get_connection()) as conn:

        # Criação das tabelas
        conn.executescript(SCHEMA)

        with conn:

            # Limpa os registros para evitar duplicações.
            # Tabelas dependentes são limpas primeiro.
            for table in (
                "order_items",
                "promotions",
                "orders",
                "products",
                "customers",
                "categories"
            ):
                conn.execute(f"DELETE FROM {table}")

            # Categorias
            conn.executemany(
                "INSERT INTO categories VALUES (?, ?, ?)",
                [
                    (
                        int(r["category_id"]),
                        r["name"],
                        r["description"]
                    )
                    for r in categories
                ]
            )

            # Clientes
            conn.executemany(
                "INSERT INTO customers VALUES (?, ?, ?, ?, ?)",
                [
                    (
                        int(r["customer_id"]),
                        r["name"],
                        r["phone"],
                        r["email"],
                        r["city"]
                    )
                    for r in customers
                ]
            )

            # Produtos
            conn.executemany(
                """
                INSERT INTO products (
                    product_id,
                    price_cents,
                    name,
                    category_id,
                    description,
                    stock_quantity,
                    status,
                    specs,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        int(r["product_id"]),
                        to_cents(r["price_brl"]),
                        r["name"],
                        int(r["category_id"]),
                        r["description"],
                        int(r["stock_quantity"]),
                        r["status"],
                        r["specs"],
                        r["created_at"]
                    )
                    for r in products
                ]
            )

            # Pedidos
            conn.executemany(
                """
                INSERT INTO orders (
                    order_id,
                    customer_id,
                    order_date,
                    status,
                    total_cents,
                    payment_method,
                    tracking_code,
                    estimated_delivery,
                    notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        int(r["order_id"]),
                        int(r["customer_id"]),
                        r["order_date"],
                        r["status"],
                        to_cents(r["total_brl"]),
                        r["payment_method"],
                        optional_text(r["tracking_code"]),
                        optional_text(r["estimated_delivery"]),
                        optional_text(r["notes"])
                    )
                    for r in orders
                ]
            )

            # Itens dos pedidos
            conn.executemany(
                """
                INSERT INTO order_items (
                    order_id,
                    product_id,
                    quantity
                )
                VALUES (?, ?, ?)
                """,
                [
                    (
                        int(r["order_id"]),
                        int(r["product_id"]),
                        int(r["quantity"])
                    )
                    for r in order_items
                ]
            )

            # Promoções
            conn.executemany(
                """
                INSERT INTO promotions (
                    promotion_id,
                    product_id,
                    discount_percent,
                    description,
                    is_active
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        int(r["promotion_id"]),
                        int(r["product_id"]),
                        int(r["discount_percent"]),
                        r["description"],
                        int(r["is_active"])
                    )
                    for r in promotions
                ]
            )

        # Exibição do resultado
        tables = (
            "categories",
            "customers",
            "products",
            "orders",
            "order_items",
            "promotions"
        )

        print("\n========== IMPORTAÇÃO ==========")

        for table in tables:
            count = conn.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]

            print(f"{table}: {count} registros")

        print(f"\nBanco pronto: {DB_PATH}")


if __name__ == "__main__":
    import_data()
