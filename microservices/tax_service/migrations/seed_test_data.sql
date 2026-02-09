-- Seed test data for tax_service

INSERT INTO tax.calculations (calculation_id, order_id, currency, total_tax, lines)
VALUES
    ('tax_test_01', 'order_test_01', 'USD', 0, '[]'::jsonb)
ON CONFLICT DO NOTHING;
