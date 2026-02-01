# Phase 01: Template Cleanup
Status: ⬜ Pending

## Objective
Remove redundant files and navigation links to prepare for the consolidated dashboard.

## Requirements
- No "Operations Overview" link in the sidebar.
- No dead files in the `templates` directory.

## Implementation Steps
1. [ ] Remove the "Operations Overview" link from `templates/sidebar.html`.
2. [ ] Delete `templates/operations_overview.html`.
3. [ ] Verify that navigating to `/` still works perfectly.

## Files to Create/Modify
- `templates/sidebar.html` - Modify
- `templates/operations_overview.html` - Delete

## Test Criteria
- Sidebar links correctly reflect the new structure.
- No 404 errors on the main dashboard navigation.
