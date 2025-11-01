-- Order Service Migration: Rename schema from "order" to "orders"
-- Version: 002
-- Date: 2025-10-27
-- Description: Rename schema to avoid SQL reserved keyword conflict

-- Rename the schema from "order" to "orders"
ALTER SCHEMA "order" RENAME TO orders;

-- Verify
SELECT 'Schema renamed successfully' as status;
