# Workbook: UserManagementSystem.xlsx

## Sheet: User Management Database

### Database Info

- System Name:: User Management System
- Module Name:: Authentication
- Db Name:: user_management
- Purpose:: Handles user authentication, profiles, and access control
- Status:: Active

### User Table

| Attribute  | Value                                                   |
| ---------- | ------------------------------------------------------- |
| Table Name | users                                                   |
| Purpose    | Stores user account information and authentication data |

#### Columns

| Column        | Data Type    | Key | Null | Description                     | Category       |
| ------------- | ------------ | --- | ---- | ------------------------------- | -------------- |
| user_id       | INT          | PRI | NO   | Unique identifier for each user | Primary        |
| username      | VARCHAR(50)  | UNI | NO   | Unique username for login       | Authentication |
| email         | VARCHAR(100) | UNI | NO   | User's email address            | Contact        |
| password_hash | VARCHAR(255) |     | NO   | Hashed password for security    | Authentication |
| first_name    | VARCHAR(50)  |     | NO   | User's first name               | Personal       |
| last_name     | VARCHAR(50)  |     | NO   | User's last name                | Personal       |
| phone         | VARCHAR(20)  |     | YES  | User's phone number             | Contact        |
| created_at    | TIMESTAMP    |     | NO   | Account creation timestamp      | Audit          |
| updated_at    | TIMESTAMP    |     | NO   | Last update timestamp           | Audit          |
| is_active     | BOOLEAN      |     | NO   | Whether account is active       | Status         |
| last_login    | TIMESTAMP    |     | YES  | Last login timestamp            | Authentication |

### User Profiles Table

| Attribute  | Value                                                      |
| ---------- | ---------------------------------------------------------- |
| Table Name | user_profiles                                              |
| Purpose    | Stores additional user profile information and preferences |

#### Columns

| Column        | Data Type    | Key | Null | Description                   | Category    |
| ------------- | ------------ | --- | ---- | ----------------------------- | ----------- |
| profile_id    | INT          | PRI | NO   | Unique profile identifier     | Primary     |
| user_id       | INT          | MUL | NO   | Foreign key to users table    | Foreign     |
| bio           | TEXT         |     | YES  | User's biography              | Personal    |
| avatar_url    | VARCHAR(255) |     | YES  | URL to user's avatar image    | Media       |
| date_of_birth | DATE         |     | YES  | User's date of birth          | Personal    |
| country       | VARCHAR(50)  |     | YES  | User's country                | Location    |
| timezone      | VARCHAR(50)  |     | YES  | User's timezone               | Location    |
| language      | VARCHAR(10)  |     | YES  | Preferred language            | Preferences |
| theme         | VARCHAR(20)  |     | YES  | UI theme preference           | Preferences |
| created_at    | TIMESTAMP    |     | NO   | Profile creation timestamp    | Audit       |
| updated_at    | TIMESTAMP    |     | NO   | Last profile update timestamp | Audit       |

### User Roles Table

| Attribute  | Value                                            |
| ---------- | ------------------------------------------------ |
| Table Name | user_roles                                       |
| Purpose    | Defines user roles and permissions in the system |

#### Columns

| Column      | Data Type   | Key | Null | Description                     | Category    |
| ----------- | ----------- | --- | ---- | ------------------------------- | ----------- |
| role_id     | INT         | PRI | NO   | Unique role identifier          | Primary     |
| role_name   | VARCHAR(50) | UNI | NO   | Name of the role                | Role        |
| description | TEXT        |     | YES  | Description of role permissions | Role        |
| permissions | JSON        |     | YES  | JSON array of permissions       | Permissions |
| is_active   | BOOLEAN     |     | NO   | Whether role is active          | Status      |
| created_at  | TIMESTAMP   |     | NO   | Role creation timestamp         | Audit       |

### User Role Assignments Table

| Attribute  | Value                               |
| ---------- | ----------------------------------- |
| Table Name | user_role_assignments               |
| Purpose    | Links users to their assigned roles |

#### Columns

| Column        | Data Type | Key | Null | Description                     | Category |
| ------------- | --------- | --- | ---- | ------------------------------- | -------- |
| assignment_id | INT       | PRI | NO   | Unique assignment identifier    | Primary  |
| user_id       | INT       | MUL | NO   | Foreign key to users table      | Foreign  |
| role_id       | INT       | MUL | NO   | Foreign key to user_roles table | Foreign  |
| assigned_by   | INT       | MUL | YES  | User who assigned this role     | Audit    |
| assigned_at   | TIMESTAMP |     | NO   | When role was assigned          | Audit    |
| expires_at    | TIMESTAMP |     | YES  | When role assignment expires    | Audit    |
| is_active     | BOOLEAN   |     | NO   | Whether assignment is active    | Status   |
