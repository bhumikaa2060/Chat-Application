-- CREATE TABLE employees (
--    employee_id   INTEGER NOT NULL,
--    first_name    VARCHAR(1000) NOT NULL,
--    last_name     VARCHAR(1000) NOT NULL,
--    date_of_birth DATE          NOT NULL,
--    phone_number  VARCHAR(1000) NOT NULL,
--    CONSTRAINT employees_pk PRIMARY KEY (employee_id)
-- )

-- INSERT INTO employees(employee_id,first_name,last_name,date_of_birth,phone_number) VALUES(2,'sanjib','kasti','2059-01-06','9864163280');

-- CREATE TABLE second_company_employees (
--    employee_id   INTEGER NOT NULL PRIMARY KEY,
--    first_name    VARCHAR(1000) NOT NULL,
--    last_name     VARCHAR(1000) NOT NULL,
--    date_of_birth DATE          NOT NULL,
--    phone_number  VARCHAR(1000) NOT NULL
-- )

-- INSERT INTO second_company_employees(employee_id,first_name,last_name,date_of_birth,phone_number) VALUES(2,'sanjib','kasti','2059-01-06','9864163280');

-- SELECT * FROM second_company_employees

-- SELECT * FROM employees where employee_id = 1

-- CREATE TABLE merged_employees (
--     employee_id   INTEGER NOT NULL,
--     subsidiary_id INTEGER NOT NULL,
--     first_name    VARCHAR(1000) NOT NULL,
--     last_name     VARCHAR(1000) NOT NULL,
--     date_of_birth DATE          NOT NULL,
--     phone_number  VARCHAR(1000) NOT NULL,
--     CONSTRAINT merged_employees_pk PRIMARY KEY (employee_id, subsidiary_id)
-- );


-- INSERT INTO merged_employees (employee_id, subsidiary_id, first_name, last_name, date_of_birth, phone_number)
-- SELECT employee_id, 1, first_name, last_name, date_of_birth, phone_number
-- FROM employees;

-- INSERT INTO merged_employees (employee_id, subsidiary_id, first_name, last_name, date_of_birth, phone_number)
-- SELECT employee_id, 2, first_name, last_name, date_of_birth, phone_number
-- FROM second_company_employees;

-- CREATE OR REPLACE FUNCTION get_age(date_of_birth DATE)
-- RETURNS INTEGER AS $$
-- BEGIN
--   RETURN TRUNC(EXTRACT(YEAR FROM AGE(current_date, date_of_birth)));
-- END;
-- $$ LANGUAGE plpgsql;


-- SELECT get_age(date_of_birth) FROM merged_employees;

SELECT count(*) FROM merged_employees WHERE last_name = 'kasti'
