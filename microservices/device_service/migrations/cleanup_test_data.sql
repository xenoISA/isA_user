-- Device Service - Cleanup Test Data
-- Remove all test data from device schema

-- Delete test device commands
DELETE FROM device.device_commands WHERE command_id LIKE 'test_%';

-- Delete test frame configs
DELETE FROM device.frame_configs WHERE device_id LIKE 'test_%';

-- Delete test device groups
DELETE FROM device.device_groups WHERE group_id LIKE 'test_%';

-- Delete test devices
DELETE FROM device.devices WHERE device_id LIKE 'test_%';

-- Verify cleanup
SELECT 'Remaining test devices:' as info, COUNT(*) as count FROM device.devices WHERE device_id LIKE 'test_%';
SELECT 'Remaining test groups:' as info, COUNT(*) as count FROM device.device_groups WHERE group_id LIKE 'test_%';
SELECT 'Remaining test configs:' as info, COUNT(*) as count FROM device.frame_configs WHERE device_id LIKE 'test_%';
SELECT 'Remaining test commands:' as info, COUNT(*) as count FROM device.device_commands WHERE command_id LIKE 'test_%';
