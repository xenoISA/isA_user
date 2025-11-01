-- Organization Service Migration: Add album and smart_frame resource types
-- Version: 003
-- Date: 2025-10-27
-- Description: Update family_sharing_resources table to support album and smart_frame resource types
--              Also adds album-specific permission levels to the permission check constraints

-- Update resource_type check constraint to include album and smart_frame
ALTER TABLE organization.family_sharing_resources
    DROP CONSTRAINT IF EXISTS sharing_resource_type_valid;

ALTER TABLE organization.family_sharing_resources
    ADD CONSTRAINT sharing_resource_type_valid CHECK (
        resource_type IN (
            'subscription',
            'device',
            'storage',
            'wallet',
            'media_library',
            'calendar',
            'shopping_list',
            'location',
            'album',        -- ✅ New: Photo album sharing for smart frames
            'smart_frame'   -- ✅ New: Smart frame device sharing
        )
    );

-- Update default_permission check constraint to include album-specific permissions
ALTER TABLE organization.family_sharing_resources
    DROP CONSTRAINT IF EXISTS sharing_default_permission_valid;

ALTER TABLE organization.family_sharing_resources
    ADD CONSTRAINT sharing_default_permission_valid CHECK (
        default_permission IN (
            'owner',
            'admin',
            'full_access',
            'read_write',
            'read_only',
            'limited',
            'view_only',
            'album_viewer',       -- ✅ New: Only view album photos
            'album_contributor',  -- ✅ New: Can add photos, not delete
            'album_editor',       -- ✅ New: Can add, delete, edit photos
            'album_manager'       -- ✅ New: Can manage album settings and permissions
        )
    );

-- Update member permissions table permission_level check constraint
ALTER TABLE organization.family_sharing_member_permissions
    DROP CONSTRAINT IF EXISTS permission_level_valid;

ALTER TABLE organization.family_sharing_member_permissions
    ADD CONSTRAINT permission_level_valid CHECK (
        permission_level IN (
            'owner',
            'admin',
            'full_access',
            'read_write',
            'read_only',
            'limited',
            'view_only',
            'album_viewer',       -- ✅ New: Only view album photos
            'album_contributor',  -- ✅ New: Can add photos, not delete
            'album_editor',       -- ✅ New: Can add, delete, edit photos
            'album_manager'       -- ✅ New: Can manage album settings and permissions
        )
    );

-- Add comments for new resource types
COMMENT ON CONSTRAINT sharing_resource_type_valid ON organization.family_sharing_resources IS
    'Valid resource types including album and smart_frame for photo sharing features';

COMMENT ON CONSTRAINT sharing_default_permission_valid ON organization.family_sharing_resources IS
    'Valid permission levels including album-specific permissions (viewer, contributor, editor, manager)';

COMMENT ON CONSTRAINT permission_level_valid ON organization.family_sharing_member_permissions IS
    'Valid permission levels including album-specific permissions (viewer, contributor, editor, manager)';
