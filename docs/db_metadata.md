# Database Metadata

## Tables

### users
| Column | Type | Null | Key | Description | Category |
|--------|------|------|-----|-------------|----------|
| id | INT | NOT NULL | PRIMARY KEY | Unique user identifier | Identity |
| username | VARCHAR(50) | NOT NULL | UNIQUE | User's login username | Identity |
| email | VARCHAR(100) | NOT NULL | UNIQUE | User's email address | Contact |
| first_name | VARCHAR(50) | NULL | - | User's first name | Personal |
| last_name | VARCHAR(50) | NULL | - | User's last name | Personal |
| created_at | TIMESTAMP | NOT NULL | - | Account creation timestamp | Audit |
| updated_at | TIMESTAMP | NOT NULL | - | Last update timestamp | Audit |
| is_active | BOOLEAN | NOT NULL | - | Whether user account is active | Status |

### orders
| Column | Type | Null | Key | Description | Category |
|--------|------|------|-----|-------------|----------|
| id | INT | NOT NULL | PRIMARY KEY | Unique order identifier | Identity |
| user_id | INT | NOT NULL | FOREIGN KEY | Reference to users table | Reference |
| order_date | DATE | NOT NULL | - | Date when order was placed | Temporal |
| total_amount | DECIMAL(10,2) | NOT NULL | - | Total order amount | Financial |
| status | VARCHAR(20) | NOT NULL | - | Order status (pending, shipped, delivered) | Status |
| shipping_address | TEXT | NULL | - | Shipping address details | Location |
| created_at | TIMESTAMP | NOT NULL | - | Order creation timestamp | Audit |

### products
| Column | Type | Null | Key | Description | Category |
|--------|------|------|-----|-------------|----------|
| id | INT | NOT NULL | PRIMARY KEY | Unique product identifier | Identity |
| name | VARCHAR(100) | NOT NULL | - | Product name | Identity |
| description | TEXT | NULL | - | Product description | Content |
| price | DECIMAL(8,2) | NOT NULL | - | Product price | Financial |
| category_id | INT | NOT NULL | FOREIGN KEY | Reference to categories table | Reference |
| stock_quantity | INT | NOT NULL | - | Available stock quantity | Inventory |
| created_at | TIMESTAMP | NOT NULL | - | Product creation timestamp | Audit |

### categories
| Column | Type | Null | Key | Description | Category |
|--------|------|------|-----|-------------|----------|
| id | INT | NOT NULL | PRIMARY KEY | Unique category identifier | Identity |
| name | VARCHAR(50) | NOT NULL | UNIQUE | Category name | Identity |
| description | TEXT | NULL | - | Category description | Content |
| parent_id | INT | NULL | FOREIGN KEY | Parent category (for hierarchies) | Reference |
| created_at | TIMESTAMP | NOT NULL | - | Category creation timestamp | Audit |

### order_items
| Column | Type | Null | Key | Description | Category |
|--------|------|------|-----|-------------|----------|
| id | INT | NOT NULL | PRIMARY KEY | Unique order item identifier | Identity |
| order_id | INT | NOT NULL | FOREIGN KEY | Reference to orders table | Reference |
| product_id | INT | NOT NULL | FOREIGN KEY | Reference to products table | Reference |
| quantity | INT | NOT NULL | - | Quantity ordered | Quantity |
| unit_price | DECIMAL(8,2) | NOT NULL | - | Price per unit at time of order | Financial |
| created_at | TIMESTAMP | NOT NULL | - | Order item creation timestamp | Audit |

## Relationships
- users (1) → (N) orders
- orders (1) → (N) order_items
- products (1) → (N) order_items
- categories (1) → (N) products
- categories (1) → (N) categories (self-referencing for hierarchies)

## Notes
- All tables use auto-incrementing integer primary keys
- Timestamps are in UTC
- Foreign keys maintain referential integrity
- Categories support hierarchical structures
