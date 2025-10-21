# Workbook: PaymentSystem.xlsx

## Sheet: Payment Processing Database

### Database Info

- System Name:: Payment Processing System
- Module Name:: Financial
- Db Name:: payment_system
- Purpose:: Handles payment processing, transactions, and financial records
- Status:: Active

### Payment Transactions Table

| Attribute  | Value                                             |
| ---------- | ------------------------------------------------- |
| Table Name | payment_transactions                              |
| Purpose    | Records all payment transactions and their status |

#### Columns

| Column                 | Data Type     | Key | Null | Description                          | Category  |
| ---------------------- | ------------- | --- | ---- | ------------------------------------ | --------- |
| transaction_id         | VARCHAR(36)   | PRI | NO   | Unique transaction identifier (UUID) | Primary   |
| user_id                | INT           | MUL | NO   | User who initiated the payment       | Foreign   |
| amount                 | DECIMAL(10,2) |     | NO   | Transaction amount                   | Financial |
| currency               | VARCHAR(3)    |     | NO   | Currency code (USD, EUR, etc.)       | Financial |
| payment_method         | VARCHAR(50)   |     | NO   | Payment method used                  | Payment   |
| status                 | VARCHAR(20)   |     | NO   | Transaction status                   | Status    |
| gateway_transaction_id | VARCHAR(100)  | UNI | YES  | External gateway transaction ID      | External  |
| gateway_response       | JSON          |     | YES  | Gateway response data                | External  |
| created_at             | TIMESTAMP     |     | NO   | Transaction creation timestamp       | Audit     |
| updated_at             | TIMESTAMP     |     | NO   | Last update timestamp                | Audit     |
| processed_at           | TIMESTAMP     |     | YES  | When transaction was processed       | Audit     |
| failure_reason         | TEXT          |     | YES  | Reason for transaction failure       | Error     |

### Payment Methods Table

| Attribute  | Value                               |
| ---------- | ----------------------------------- |
| Table Name | payment_methods                     |
| Purpose    | Stores user's saved payment methods |

#### Columns

| Column       | Data Type   | Key | Null | Description                        | Category    |
| ------------ | ----------- | --- | ---- | ---------------------------------- | ----------- |
| method_id    | INT         | PRI | NO   | Unique payment method identifier   | Primary     |
| user_id      | INT         | MUL | NO   | User who owns this payment method  | Foreign     |
| method_type  | VARCHAR(20) |     | NO   | Type of payment method             | Payment     |
| provider     | VARCHAR(50) |     | NO   | Payment provider                   | Payment     |
| last_four    | VARCHAR(4)  |     | NO   | Last four digits of card/account   | Security    |
| expiry_month | INT         |     | YES  | Card expiry month                  | Security    |
| expiry_year  | INT         |     | YES  | Card expiry year                   | Security    |
| is_default   | BOOLEAN     |     | NO   | Whether this is the default method | Preferences |
| is_active    | BOOLEAN     |     | NO   | Whether method is active           | Status      |
| created_at   | TIMESTAMP   |     | NO   | Method creation timestamp          | Audit       |
| updated_at   | TIMESTAMP   |     | NO   | Last update timestamp              | Audit       |

### Refunds Table

| Attribute  | Value                                           |
| ---------- | ----------------------------------------------- |
| Table Name | refunds                                         |
| Purpose    | Tracks refund transactions and their processing |

#### Columns

| Column            | Data Type     | Key | Null | Description                         | Category  |
| ----------------- | ------------- | --- | ---- | ----------------------------------- | --------- |
| refund_id         | VARCHAR(36)   | PRI | NO   | Unique refund identifier (UUID)     | Primary   |
| transaction_id    | VARCHAR(36)   | MUL | NO   | Original transaction being refunded | Foreign   |
| amount            | DECIMAL(10,2) |     | NO   | Refund amount                       | Financial |
| reason            | TEXT          |     | YES  | Reason for refund                   | Business  |
| status            | VARCHAR(20)   |     | NO   | Refund status                       | Status    |
| processed_by      | INT           | MUL | YES  | User who processed the refund       | Audit     |
| processed_at      | TIMESTAMP     |     | YES  | When refund was processed           | Audit     |
| created_at        | TIMESTAMP     |     | NO   | Refund creation timestamp           | Audit     |
| gateway_refund_id | VARCHAR(100)  | UNI | YES  | External gateway refund ID          | External  |

### Payment Gateways Table

| Attribute  | Value                                        |
| ---------- | -------------------------------------------- |
| Table Name | payment_gateways                             |
| Purpose    | Configuration for different payment gateways |

#### Columns

| Column               | Data Type    | Key | Null | Description                 | Category      |
| -------------------- | ------------ | --- | ---- | --------------------------- | ------------- |
| gateway_id           | INT          | PRI | NO   | Unique gateway identifier   | Primary       |
| gateway_name         | VARCHAR(50)  | UNI | NO   | Name of the payment gateway | Gateway       |
| provider             | VARCHAR(50)  |     | NO   | Gateway provider company    | Gateway       |
| api_endpoint         | VARCHAR(255) |     | NO   | API endpoint URL            | Configuration |
| api_key              | VARCHAR(255) |     | NO   | API authentication key      | Security      |
| webhook_secret       | VARCHAR(255) |     | YES  | Webhook verification secret | Security      |
| supported_currencies | JSON         |     | NO   | Supported currency codes    | Configuration |
| is_active            | BOOLEAN      |     | NO   | Whether gateway is active   | Status        |
| created_at           | TIMESTAMP    |     | NO   | Gateway creation timestamp  | Audit         |
| updated_at           | TIMESTAMP    |     | NO   | Last update timestamp       | Audit         |
