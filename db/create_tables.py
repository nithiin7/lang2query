import mysql.connector
import kagglehub
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.types import Integer, Float, String

from app.config import get_database_config, ACTIVE_DATABASE

def connect_to_mysql():
    """Connect to MySQL Server using configuration."""
    # Get database config
    db_config = get_database_config()
    
    # Parse connection string to extract credentials
    connection_string = db_config["connection_string"]
    
    # For MySQL, parse the connection string
    if "mysql" in connection_string:
        # Extract parts from mysql+mysqlconnector://user:pass@host/db
        parts = connection_string.replace("mysql+mysqlconnector://", "").split("@")
        if len(parts) == 2:
            user_pass = parts[0].split(":")
            host_db = parts[1].split("/")
            
            if len(user_pass) == 2 and len(host_db) == 2:
                user = user_pass[0]
                password = user_pass[1]
                host = host_db[0]
                database = host_db[1]
                
                connection = mysql.connector.connect(
                    host=host,
                    user=user,
                    password=password
                )
                print(f"Connected to MySQL at {host}")
                return connection, database
    
    # Fallback to default values
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="<password>"
    )
    print("Connected to MySQL (using fallback)")
    return connection, "txt2sql"

def create_database(connection, database_name):
    """Create a database if it doesn't exist."""
    cursor = connection.cursor()
    
    try:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database_name}")
        print(f"Database '{database_name}' ready!")
    except Exception as e:
        print(f"Error creating database: {e}")
    finally:
        cursor.close()

def download_dataset():
    """Downloads dataset from Kaggle."""
    print("Downloading dataset from Kaggle...")
    
    try:
        # Download latest version
        path = kagglehub.dataset_download("olistbr/brazilian-ecommerce")
        print("Path to dataset files:", path)
        return path
    except Exception as e:
        print(f"Error downloading dataset: {e}")
        print("Please ensure you have kaggle credentials configured")
        return None

def create_table_from_csv(csv_file: str, table_name: str, database_name: str):
    """Create a table from CSV file."""
    try:
        df = pd.read_csv(csv_file)
        
        # Get database config
        db_config = get_database_config()
        engine = create_engine(db_config["connection_string"])
        
        # Write the DataFrame to MySQL table
        df.to_sql(name=table_name, con=engine, index=False, if_exists='replace')
        
        print(f"Data has been written to the '{table_name}' table in the '{database_name}' database.")
        return True
        
    except Exception as e:
        print(f"Error creating table {table_name}: {e}")
        return False

def create_all_tables(database_name: str):
    """Create all tables from the dataset."""
    table_configs = [
        ("olist_customers_dataset.csv", "customer"),
        ("olist_order_items_dataset.csv", "order_items"),
        ("olist_order_payments_dataset.csv", "order_payments"),
        ("olist_order_reviews_dataset.csv", "order_reviews"),
        ("olist_orders_dataset.csv", "orders"),
        ("olist_products_dataset.csv", "products"),
        ("olist_sellers_dataset.csv", "sellers"),
        ("product_category_name_translation.csv", "category_translation"),
    ]
    
    success_count = 0
    for csv_file, table_name in table_configs:
        if create_table_from_csv(csv_file, table_name, database_name):
            success_count += 1
    
    print(f"Successfully created {success_count}/{len(table_configs)} tables")

def create_indexes(database_name: str):
    """Create database indexes for better performance."""
    print("Creating database indexes...")
    
    # Get database config
    db_config = get_database_config()
    engine = create_engine(db_config["connection_string"])
    
    index_queries = [
        "CREATE INDEX IF NOT EXISTS idx_customer_id ON orders (customer_id(20))",
        "CREATE INDEX IF NOT EXISTS idx_order_id ON orders (order_id(20))",
        "ALTER TABLE orders MODIFY order_purchase_timestamp DATETIME",
        "CREATE INDEX IF NOT EXISTS idx_order_purchase_timestamp ON orders (order_purchase_timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_customer_id ON customer (customer_id(20))",
        "CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items (order_id(20))",
        "CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items (product_id(20))",
        "CREATE INDEX IF NOT EXISTS idx_order_items_seller_id ON order_items (seller_id(20))",
        "CREATE INDEX IF NOT EXISTS idx_seller_id ON sellers (seller_id(20))",
        "CREATE INDEX IF NOT EXISTS idx_product_id ON products (product_id(20))",
        "CREATE INDEX IF NOT EXISTS idx_product_category ON products (product_category_name(20))",
        "CREATE INDEX IF NOT EXISTS idx_order_reviews_order_id ON order_reviews (order_id(20))",
        "CREATE INDEX IF NOT EXISTS idx_review_score ON order_reviews (review_score)",
        "CREATE INDEX IF NOT EXISTS idx_order_payments_order_id ON order_payments (order_id(20))",
        "CREATE INDEX IF NOT EXISTS idx_payment_type ON order_payments (payment_type(20))",
        "CREATE INDEX IF NOT EXISTS idx_category_translation ON category_translation (product_category_name(20))"
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
    """Main function to set up the database."""
    print(f"Setting up database for {ACTIVE_DATABASE}")
    
    # Connect to MySQL
    connection, database_name = connect_to_mysql()
    
    try:
        # Create database if needed
        create_database(connection, database_name)
        
        # Download dataset
        dataset_path = download_dataset()
        if not dataset_path:
            print("Skipping table creation due to dataset download failure")
            return
        
        # Create all tables
        create_all_tables(database_name)
        
        # Create indexes
        create_indexes(database_name)
        
        print("Database setup completed successfully!")
        
    except Exception as e:
        print(f"Error during database setup: {e}")
    finally:
        connection.close()

if __name__ == "__main__":
    main()
