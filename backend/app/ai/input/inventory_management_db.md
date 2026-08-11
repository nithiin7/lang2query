# Workbook: InventoryManagement.xlsx

## Sheet: Inventory Management Database

### Database Info

- System Name:: Inventory Management System
- Module Name:: Operations
- Db Name:: inventory_management
- Purpose:: Manages product inventory, stock levels, and warehouse operations
- Status:: Active

### Products Table

| Attribute  | Value                                        |
| ---------- | -------------------------------------------- |
| Table Name | products                                     |
| Purpose    | Master catalog of all products in the system |

#### Columns

| Column      | Data Type     | Key | Null | Description                  | Category  |
| ----------- | ------------- | --- | ---- | ---------------------------- | --------- |
| product_id  | INT           | PRI | NO   | Unique product identifier    | Primary   |
| sku         | VARCHAR(50)   | UNI | NO   | Stock Keeping Unit code      | Product   |
| name        | VARCHAR(200)  |     | NO   | Product name                 | Product   |
| description | TEXT          |     | YES  | Detailed product description | Product   |
| category_id | INT           | MUL | NO   | Product category             | Foreign   |
| brand       | VARCHAR(100)  |     | YES  | Product brand                | Product   |
| unit_price  | DECIMAL(10,2) |     | NO   | Price per unit               | Financial |
| cost_price  | DECIMAL(10,2) |     | NO   | Cost per unit                | Financial |
| weight      | DECIMAL(8,3)  |     | YES  | Product weight in kg         | Physical  |
| dimensions  | VARCHAR(100)  |     | YES  | Product dimensions           | Physical  |
| is_active   | BOOLEAN       |     | NO   | Whether product is active    | Status    |
| created_at  | TIMESTAMP     |     | NO   | Product creation timestamp   | Audit     |
| updated_at  | TIMESTAMP     |     | NO   | Last update timestamp        | Audit     |

### Inventory Table

| Attribute  | Value                                        |
| ---------- | -------------------------------------------- |
| Table Name | inventory                                    |
| Purpose    | Tracks current stock levels for each product |

#### Columns

| Column             | Data Type | Key | Null | Description                             | Category |
| ------------------ | --------- | --- | ---- | --------------------------------------- | -------- |
| inventory_id       | INT       | PRI | NO   | Unique inventory record identifier      | Primary  |
| product_id         | INT       | MUL | NO   | Foreign key to products table           | Foreign  |
| warehouse_id       | INT       | MUL | NO   | Warehouse location                      | Foreign  |
| quantity_on_hand   | INT       |     | NO   | Current stock quantity                  | Stock    |
| quantity_reserved  | INT       |     | NO   | Reserved quantity                       | Stock    |
| quantity_available | INT       |     | NO   | Available quantity (on_hand - reserved) | Stock    |
| reorder_point      | INT       |     | NO   | Minimum stock level for reordering      | Stock    |
| reorder_quantity   | INT       |     | NO   | Quantity to order when reordering       | Stock    |
| last_counted       | TIMESTAMP |     | YES  | Last physical count date                | Audit    |
| updated_at         | TIMESTAMP |     | NO   | Last update timestamp                   | Audit    |

### Warehouses Table

| Attribute  | Value                                 |
| ---------- | ------------------------------------- |
| Table Name | warehouses                            |
| Purpose    | Information about warehouse locations |

#### Columns

| Column         | Data Type    | Key | Null | Description                  | Category |
| -------------- | ------------ | --- | ---- | ---------------------------- | -------- |
| warehouse_id   | INT          | PRI | NO   | Unique warehouse identifier  | Primary  |
| warehouse_code | VARCHAR(20)  | UNI | NO   | Warehouse code               | Location |
| name           | VARCHAR(100) |     | NO   | Warehouse name               | Location |
| address        | TEXT         |     | NO   | Warehouse address            | Location |
| city           | VARCHAR(50)  |     | NO   | City                         | Location |
| state          | VARCHAR(50)  |     | NO   | State/Province               | Location |
| country        | VARCHAR(50)  |     | NO   | Country                      | Location |
| postal_code    | VARCHAR(20)  |     | NO   | Postal/ZIP code              | Location |
| contact_person | VARCHAR(100) |     | YES  | Warehouse contact person     | Contact  |
| phone          | VARCHAR(20)  |     | YES  | Warehouse phone number       | Contact  |
| email          | VARCHAR(100) |     | YES  | Warehouse email              | Contact  |
| is_active      | BOOLEAN      |     | NO   | Whether warehouse is active  | Status   |
| created_at     | TIMESTAMP    |     | NO   | Warehouse creation timestamp | Audit    |

### Stock Movements Table

| Attribute  | Value                                                        |
| ---------- | ------------------------------------------------------------ |
| Table Name | stock_movements                                              |
| Purpose    | Records all stock movements (inbound, outbound, adjustments) |

#### Columns

| Column           | Data Type    | Key | Null | Description                           | Category  |
| ---------------- | ------------ | --- | ---- | ------------------------------------- | --------- |
| movement_id      | INT          | PRI | NO   | Unique movement identifier            | Primary   |
| product_id       | INT          | MUL | NO   | Product being moved                   | Foreign   |
| warehouse_id     | INT          | MUL | NO   | Warehouse involved                    | Foreign   |
| movement_type    | VARCHAR(20)  |     | NO   | Type of movement                      | Movement  |
| quantity         | INT          |     | NO   | Quantity moved (positive for inbound) | Movement  |
| reference_number | VARCHAR(50)  |     | YES  | Reference number (PO, SO, etc.)       | Reference |
| reason           | VARCHAR(100) |     | YES  | Reason for movement                   | Movement  |
| performed_by     | INT          | MUL | YES  | User who performed the movement       | Audit     |
| movement_date    | TIMESTAMP    |     | NO   | When movement occurred                | Audit     |
| created_at       | TIMESTAMP    |     | NO   | Record creation timestamp             | Audit     |

### Product Categories Table

| Attribute  | Value                               |
| ---------- | ----------------------------------- |
| Table Name | product_categories                  |
| Purpose    | Hierarchical product categorization |

#### Columns

| Column             | Data Type    | Key | Null | Description                   | Category |
| ------------------ | ------------ | --- | ---- | ----------------------------- | -------- |
| category_id        | INT          | PRI | NO   | Unique category identifier    | Primary  |
| parent_category_id | INT          | MUL | YES  | Parent category for hierarchy | Foreign  |
| category_name      | VARCHAR(100) |     | NO   | Category name                 | Category |
| description        | TEXT         |     | YES  | Category description          | Category |
| sort_order         | INT          |     | NO   | Display order                 | Category |
| is_active          | BOOLEAN      |     | NO   | Whether category is active    | Status   |
| created_at         | TIMESTAMP    |     | NO   | Category creation timestamp   | Audit    |
| updated_at         | TIMESTAMP    |     | NO   | Last update timestamp         | Audit    |
