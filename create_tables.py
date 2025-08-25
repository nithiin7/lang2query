import mysql.connector
import kagglehub
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.types import Integer, Float, String

def connect_to_mysql():
    # Connect to MySQL Server
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="<password>"
    )
    print("Connected to MySQL")
    return connection

def create_database(connection):
    # Create a cursor to execute SQL commands
    cursor = connection.cursor()
    
    # Replace 'my_new_db' with your desired database name
    cursor.execute("CREATE DATABASE txt2sql")
    
    print("Database 'txt2sql' created successfully!")
    cursor.close()

def download_dataset():
    # Downloads dataset from kaggle
    # Soon after it downloads pull the files to current folder
    print("Downloading dataset from Kaggle...")
    
    # Download latest version
    path = kagglehub.dataset_download("olistbr/brazilian-ecommerce")
    print("Path to dataset files:", path)
    return path

def create_customer_table():
    df = pd.read_csv('olist_customers_dataset.csv')  # Replace with your CSV file path
    
    # Set up SQLAlchemy engine with your MySQL credentials
    engine = create_engine('mysql+mysqlconnector://root:<password>@localhost/txt2sql')
    
    # Write the DataFrame to a new MySQL table
    df.to_sql(name='customer', con=engine, index=False, if_exists='replace')  # or 'append'
    
    print("Data has been written to the 'customer' table in the 'txt2sql' database.")

def create_order_items_table():
    df = pd.read_csv('olist_order_items_dataset.csv')  # Replace with your CSV file path
    
    # Set up SQLAlchemy engine with your MySQL credentials
    engine = create_engine('mysql+mysqlconnector://root:<password>@localhost/txt2sql')
    
    # Write the DataFrame to a new MySQL table
    df.to_sql(name='order_items', con=engine, index=False, if_exists='replace')  # or 'append'
    
    print("Data has been written to the 'order_items' table in the 'txt2sql' database.")

def create_order_payments_table():
    df = pd.read_csv('olist_order_payments_dataset.csv')  # Replace with your CSV file path
    
    # Set up SQLAlchemy engine with your MySQL credentials
    engine = create_engine('mysql+mysqlconnector://root:<password>@localhost/txt2sql')
    
    # Write the DataFrame to a new MySQL table
    df.to_sql(name='order_payments', con=engine, index=False, if_exists='replace')  # or 'append'
    
    print("Data has been written to the 'order_payments' table in the 'txt2sql' database.")

def create_order_reviews_table():
    df = pd.read_csv('olist_order_reviews_dataset.csv')  # Replace with your CSV file path
    
    # Set up SQLAlchemy engine with your MySQL credentials
    engine = create_engine('mysql+mysqlconnector://root:<password>@localhost/txt2sql')
    
    # Write the DataFrame to a new MySQL table
    df.to_sql(name='order_reviews', con=engine, index=False, if_exists='replace')  # or 'append'
    
    print("Data has been written to the 'order_reviews' table in the 'txt2sql' database.")

def create_orders_table():
    df = pd.read_csv('olist_orders_dataset.csv')  # Replace with your CSV file path
    
    # Set up SQLAlchemy engine with your MySQL credentials
    engine = create_engine('mysql+mysqlconnector://root:<password>@localhost/txt2sql')
    
    # Write the DataFrame to a new MySQL table
    df.to_sql(name='orders', con=engine, index=False, if_exists='replace')  # or 'append'
    
    print("Data has been written to the 'orders' table in the 'txt2sql' database.")

def create_products_table():
    df = pd.read_csv('olist_products_dataset.csv')  # Replace with your CSV file path
    
    # Set up SQLAlchemy engine with your MySQL credentials
    engine = create_engine('mysql+mysqlconnector://root:<password>@localhost/txt2sql')
    
    # Write the DataFrame to a new MySQL table
    df.to_sql(name='products', con=engine, index=False, if_exists='replace')  # or 'append'
    
    print("Data has been written to the 'products' table in the 'txt2sql' database.")

def create_sellers_table():
    df = pd.read_csv('olist_sellers_dataset.csv')  # Replace with your CSV file path
    
    # Set up SQLAlchemy engine with your MySQL credentials
    engine = create_engine('mysql+mysqlconnector://root:<password>@localhost/txt2sql')
    
    # Write the DataFrame to a new MySQL table
    df.to_sql(name='sellers', con=engine, index=False, if_exists='replace')  # or 'append'
    
    print("Data has been written to the 'sellers' table in the 'txt2sql' database.")

def create_category_translation_table():
    df = pd.read_csv('product_category_name_translation.csv')  # Replace with your CSV file path
    
    # Set up SQLAlchemy engine with your MySQL credentials
    engine = create_engine('mysql+mysqlconnector://root:<password>@localhost/txt2sql')
    
    # Write the DataFrame to a new MySQL table
    df.to_sql(name='category_translation', con=engine, index=False, if_exists='replace')  # or 'append'
    
    print("Data has been written to the 'category_translation' table in the 'txt2sql' database.")

def create_indexes():
    # Indexes
    # Create below indexes so that joins are faster
    
    engine = create_engine('mysql+mysqlconnector://root:<password>@localhost/txt2sql')
    
    index_queries = [
        "CREATE INDEX idx_customer_id ON orders (customer_id(20))",
        "CREATE INDEX idx_order_id ON orders (order_id(20))",
        "ALTER TABLE orders MODIFY order_purchase_timestamp DATETIME",
        "CREATE INDEX idx_order_purchase_timestamp ON orders (order_purchase_timestamp)",
        "CREATE INDEX idx_customer_id ON customer (customer_id(20))",
        "CREATE INDEX idx_order_items_order_id ON order_items (order_id(20))",
        "CREATE INDEX idx_order_items_product_id ON order_items (product_id(20))",
        "CREATE INDEX idx_order_items_seller_id ON order_items (seller_id(20))",
        "CREATE INDEX idx_seller_id ON sellers (seller_id(20))",
        "CREATE INDEX idx_product_id ON products (product_id(20))",
        "CREATE INDEX idx_product_category ON products (product_category_name(20))",
        "CREATE INDEX idx_order_reviews_order_id ON order_reviews (order_id(20))",
        "CREATE INDEX idx_review_score ON order_reviews (review_score)",
        "CREATE INDEX idx_order_payments_order_id ON order_payments (order_id(20))",
        "CREATE INDEX idx_payment_type ON order_payments (payment_type(20))",
        "CREATE INDEX idx_category_translation ON category_translation (product_category_name(20))"
    ]
    
    with engine.connect() as conn:
        for query in index_queries:
            try:
                conn.execute(text(query))
                print(f"Executed: {query}")
            except Exception as e:
                print(f"Error executing {query}: {e}")
        conn.commit()

def main():
    # Connect to MySQL
    connection = connect_to_mysql()
    
    # Create database (uncomment if needed)
    # create_database(connection)
    
    # Download dataset
    download_dataset()
    
    # Create all tables
    create_customer_table()
    create_order_items_table()
    create_order_payments_table()
    create_order_reviews_table()
    create_orders_table()
    create_products_table()
    create_sellers_table()
    create_category_translation_table()
    
    # Create indexes
    create_indexes()
    
    connection.close()
    print("All tables created successfully!")

if __name__ == "__main__":
    main()
