-- ============================================================
-- Enterprise Platform — Sample Business Database Schema & Data
-- ============================================================
-- Run: sqlite3 data/enterprise.db < data/sample_db.sql
-- ============================================================

-- Departments
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    budget REAL DEFAULT 0,
    manager_id INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO departments (id, name, budget) VALUES
    (1, 'Engineering', 2500000),
    (2, 'Sales', 1800000),
    (3, 'Marketing', 1200000),
    (4, 'Human Resources', 800000),
    (5, 'Finance', 950000),
    (6, 'Operations', 1100000),
    (7, 'Customer Support', 700000),
    (8, 'Research & Development', 3000000);

-- Employees
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    department_id INTEGER REFERENCES departments(id),
    position TEXT,
    salary REAL,
    hire_date TEXT,
    is_active INTEGER DEFAULT 1
);

INSERT OR IGNORE INTO employees (id, name, email, department_id, position, salary, hire_date) VALUES
    (1, 'Alice Chen', 'alice.chen@company.com', 1, 'VP of Engineering', 185000, '2019-03-15'),
    (2, 'Bob Martinez', 'bob.martinez@company.com', 1, 'Senior Software Engineer', 155000, '2020-06-01'),
    (3, 'Carol Williams', 'carol.williams@company.com', 1, 'Software Engineer', 125000, '2021-09-20'),
    (4, 'David Kim', 'david.kim@company.com', 1, 'DevOps Engineer', 140000, '2020-11-05'),
    (5, 'Eva Brown', 'eva.brown@company.com', 1, 'ML Engineer', 160000, '2021-01-10'),
    (6, 'Frank Johnson', 'frank.johnson@company.com', 2, 'VP of Sales', 175000, '2018-07-22'),
    (7, 'Grace Lee', 'grace.lee@company.com', 2, 'Senior Sales Manager', 130000, '2019-11-18'),
    (8, 'Henry Davis', 'henry.davis@company.com', 2, 'Account Executive', 95000, '2021-04-03'),
    (9, 'Iris Taylor', 'iris.taylor@company.com', 2, 'Sales Representative', 85000, '2022-02-14'),
    (10, 'Jack Wilson', 'jack.wilson@company.com', 3, 'Marketing Director', 145000, '2019-05-30'),
    (11, 'Karen White', 'karen.white@company.com', 3, 'Content Strategist', 95000, '2021-08-12'),
    (12, 'Leo Garcia', 'leo.garcia@company.com', 3, 'Digital Marketing Manager', 110000, '2020-03-25'),
    (13, 'Mia Anderson', 'mia.anderson@company.com', 4, 'HR Director', 140000, '2018-12-01'),
    (14, 'Noah Thomas', 'noah.thomas@company.com', 4, 'HR Specialist', 78000, '2022-06-20'),
    (15, 'Olivia Moore', 'olivia.moore@company.com', 5, 'CFO', 195000, '2017-09-15'),
    (16, 'Peter Jackson', 'peter.jackson@company.com', 5, 'Financial Analyst', 105000, '2021-03-08'),
    (17, 'Quinn Harris', 'quinn.harris@company.com', 6, 'Operations Manager', 120000, '2020-07-14'),
    (18, 'Rachel Clark', 'rachel.clark@company.com', 7, 'Support Lead', 90000, '2021-11-30'),
    (19, 'Sam Robinson', 'sam.robinson@company.com', 8, 'Research Scientist', 165000, '2020-01-22'),
    (20, 'Tara Lewis', 'tara.lewis@company.com', 8, 'Data Scientist', 150000, '2021-05-17');

-- Update department managers
UPDATE departments SET manager_id = 1 WHERE id = 1;
UPDATE departments SET manager_id = 6 WHERE id = 2;
UPDATE departments SET manager_id = 10 WHERE id = 3;
UPDATE departments SET manager_id = 13 WHERE id = 4;
UPDATE departments SET manager_id = 15 WHERE id = 5;
UPDATE departments SET manager_id = 17 WHERE id = 6;
UPDATE departments SET manager_id = 18 WHERE id = 7;
UPDATE departments SET manager_id = 19 WHERE id = 8;

-- Products
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT,
    price REAL,
    stock_quantity INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1
);

INSERT OR IGNORE INTO products (id, name, category, price, stock_quantity) VALUES
    (1, 'Enterprise Suite Pro', 'Software', 999.00, 500),
    (2, 'Analytics Dashboard', 'Software', 599.00, 750),
    (3, 'Cloud Storage (1TB)', 'Service', 49.99, 9999),
    (4, 'Premium Support', 'Service', 199.99, 9999),
    (5, 'Data Integration Toolkit', 'Software', 349.00, 300),
    (6, 'API Gateway Pro', 'Software', 799.00, 400),
    (7, 'Security Audit Package', 'Service', 2499.00, 100),
    (8, 'ML Pipeline Starter', 'Software', 449.00, 250);

-- Customers
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT,
    company TEXT,
    region TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO customers (id, name, email, company, region) VALUES
    (1, 'TechCorp Inc.', 'procurement@techcorp.com', 'TechCorp', 'North'),
    (2, 'DataFlow Systems', 'sales@dataflow.io', 'DataFlow', 'East'),
    (3, 'CloudFirst Ltd.', 'orders@cloudfirst.com', 'CloudFirst', 'West'),
    (4, 'InnovateTech', 'buying@innovatetech.com', 'InnovateTech', 'South'),
    (5, 'GlobalServe Corp', 'purchasing@globalserve.com', 'GlobalServe', 'North'),
    (6, 'NexGen Solutions', 'info@nexgen.com', 'NexGen', 'East'),
    (7, 'PrimeLogic Inc.', 'vendor@primelogic.com', 'PrimeLogic', 'West'),
    (8, 'Quantum Dynamics', 'ops@quantumdyn.com', 'Quantum Dynamics', 'South'),
    (9, 'AlphaEdge Corp', 'supply@alphaedge.com', 'AlphaEdge', 'North'),
    (10, 'MetaVerse Tech', 'business@metaverse-tech.com', 'MetaVerse', 'East');

-- Sales
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER REFERENCES products(id),
    customer_id INTEGER REFERENCES customers(id),
    amount REAL,
    quantity INTEGER,
    sale_date TEXT,
    region TEXT,
    quarter TEXT
);

INSERT OR IGNORE INTO sales (id, product_id, customer_id, amount, quantity, sale_date, region, quarter) VALUES
    (1, 1, 1, 4995.00, 5, '2024-01-15', 'North', 'Q1'),
    (2, 2, 2, 2995.00, 5, '2024-01-22', 'East', 'Q1'),
    (3, 3, 3, 499.90, 10, '2024-02-10', 'West', 'Q1'),
    (4, 1, 4, 9990.00, 10, '2024-02-18', 'South', 'Q1'),
    (5, 4, 5, 3999.80, 20, '2024-03-05', 'North', 'Q1'),
    (6, 6, 6, 7990.00, 10, '2024-03-12', 'East', 'Q1'),
    (7, 2, 7, 5990.00, 10, '2024-04-08', 'West', 'Q2'),
    (8, 5, 8, 3490.00, 10, '2024-04-22', 'South', 'Q2'),
    (9, 1, 9, 14985.00, 15, '2024-05-03', 'North', 'Q2'),
    (10, 7, 10, 24990.00, 10, '2024-05-18', 'East', 'Q2'),
    (11, 3, 1, 2499.50, 50, '2024-06-01', 'North', 'Q2'),
    (12, 8, 2, 4490.00, 10, '2024-06-15', 'East', 'Q2'),
    (13, 1, 3, 19980.00, 20, '2024-07-02', 'West', 'Q3'),
    (14, 2, 4, 8970.00, 15, '2024-07-20', 'South', 'Q3'),
    (15, 4, 5, 5999.70, 30, '2024-08-05', 'North', 'Q3'),
    (16, 6, 6, 15980.00, 20, '2024-08-22', 'East', 'Q3'),
    (17, 5, 7, 6980.00, 20, '2024-09-01', 'West', 'Q3'),
    (18, 7, 8, 49980.00, 20, '2024-09-15', 'South', 'Q3'),
    (19, 8, 9, 8980.00, 20, '2024-09-28', 'North', 'Q3'),
    (20, 1, 10, 29970.00, 30, '2024-10-05', 'East', 'Q4');

-- Orders
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER REFERENCES customers(id),
    order_date TEXT,
    total_amount REAL,
    status TEXT DEFAULT 'pending'
);

INSERT OR IGNORE INTO orders (id, customer_id, order_date, total_amount, status) VALUES
    (1, 1, '2024-01-15', 4995.00, 'completed'),
    (2, 2, '2024-01-22', 2995.00, 'completed'),
    (3, 3, '2024-02-10', 499.90, 'completed'),
    (4, 4, '2024-02-18', 9990.00, 'completed'),
    (5, 5, '2024-03-05', 3999.80, 'completed'),
    (6, 6, '2024-03-12', 7990.00, 'shipped'),
    (7, 7, '2024-04-08', 5990.00, 'completed'),
    (8, 8, '2024-04-22', 3490.00, 'completed'),
    (9, 9, '2024-05-03', 14985.00, 'processing'),
    (10, 10, '2024-05-18', 24990.00, 'completed');
