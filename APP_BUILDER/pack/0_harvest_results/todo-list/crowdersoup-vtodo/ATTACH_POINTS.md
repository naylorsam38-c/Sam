# Attach Points

Application: CrowderSoup/vTodo
Repository: CrowderSoup/vTodo
Commit: 
Framework: django
Datastore: postgresql

## Events
| Name | Source | Symbol | Payload | Implementation | Evidence |
|------|--------|--------|---------|----------------|----------|

## Slots
| Name | Source | Rendering Context | Implementation | Evidence |
|------|--------|-------------------|----------------|----------|
| CrowderSoup__vTodo.login.body_class | templates/login.html | apps/accounts/views.py | NATIVE | templates/login.html:5, apps/accounts/views.py |
| CrowderSoup__vTodo.login.title | templates/login.html | apps/accounts/views.py | NATIVE | templates/login.html:6, apps/accounts/views.py |
| CrowderSoup__vTodo.login.content | templates/login.html | apps/accounts/views.py | NATIVE | templates/login.html:8, apps/accounts/views.py |
| CrowderSoup__vTodo.base.title | templates/base.html | (extended by a child template) | NATIVE | templates/base.html:7 |
| CrowderSoup__vTodo.base.body_class | templates/base.html | (extended by a child template) | NATIVE | templates/base.html:26 |
| CrowderSoup__vTodo.base.content | templates/base.html | (extended by a child template) | NATIVE | templates/base.html:118 |
| CrowderSoup__vTodo.base.extra_scripts | templates/base.html | (extended by a child template) | NATIVE | templates/base.html:121 |
| CrowderSoup__vTodo.invite_accept.body_class | templates/teams/invite_accept.html | apps/teams/views.py | NATIVE | templates/teams/invite_accept.html:3, apps/teams/views.py |
| CrowderSoup__vTodo.invite_accept.title | templates/teams/invite_accept.html | apps/teams/views.py | NATIVE | templates/teams/invite_accept.html:4, apps/teams/views.py |
| CrowderSoup__vTodo.invite_accept.content | templates/teams/invite_accept.html | apps/teams/views.py | NATIVE | templates/teams/invite_accept.html:6, apps/teams/views.py |
| CrowderSoup__vTodo.general.settings_title | templates/users/settings/general.html | apps/users/views.py | NATIVE | templates/users/settings/general.html:3, apps/users/views.py |
| CrowderSoup__vTodo.general.settings_content | templates/users/settings/general.html | apps/users/views.py | NATIVE | templates/users/settings/general.html:5, apps/users/views.py |
| CrowderSoup__vTodo.board.settings_title | templates/users/settings/board.html | apps/users/views.py | NATIVE | templates/users/settings/board.html:3, apps/users/views.py |
| CrowderSoup__vTodo.board.settings_header | templates/users/settings/board.html | apps/users/views.py | NATIVE | templates/users/settings/board.html:5, apps/users/views.py |
| CrowderSoup__vTodo.board.settings_content | templates/users/settings/board.html | apps/users/views.py | NATIVE | templates/users/settings/board.html:15, apps/users/views.py |
| CrowderSoup__vTodo.calendar.settings_title | templates/users/settings/calendar.html | apps/users/views.py | NATIVE | templates/users/settings/calendar.html:3, apps/users/views.py |
| CrowderSoup__vTodo.calendar.settings_header | templates/users/settings/calendar.html | apps/users/views.py | NATIVE | templates/users/settings/calendar.html:5, apps/users/views.py |
| CrowderSoup__vTodo.calendar.settings_content | templates/users/settings/calendar.html | apps/users/views.py | NATIVE | templates/users/settings/calendar.html:15, apps/users/views.py |
| CrowderSoup__vTodo.teams.settings_title | templates/users/settings/teams.html | apps/users/views.py | NATIVE | templates/users/settings/teams.html:3, apps/users/views.py |
| CrowderSoup__vTodo.teams.settings_header | templates/users/settings/teams.html | apps/users/views.py | NATIVE | templates/users/settings/teams.html:5, apps/users/views.py |
| CrowderSoup__vTodo.teams.settings_content | templates/users/settings/teams.html | apps/users/views.py | NATIVE | templates/users/settings/teams.html:15, apps/users/views.py |
| CrowderSoup__vTodo.api.settings_title | templates/users/settings/api.html | apps/users/views.py | NATIVE | templates/users/settings/api.html:3, apps/users/views.py |
| CrowderSoup__vTodo.api.settings_header | templates/users/settings/api.html | apps/users/views.py | NATIVE | templates/users/settings/api.html:5, apps/users/views.py |
| CrowderSoup__vTodo.api.settings_content | templates/users/settings/api.html | apps/users/views.py | NATIVE | templates/users/settings/api.html:15, apps/users/views.py |
| CrowderSoup__vTodo._base.body_class | templates/users/settings/_base.html | (extended by a child template) | NATIVE | templates/users/settings/_base.html:3 |
| CrowderSoup__vTodo._base.title | templates/users/settings/_base.html | (extended by a child template) | NATIVE | templates/users/settings/_base.html:4 |
| CrowderSoup__vTodo._base.settings_title | templates/users/settings/_base.html | (extended by a child template) | NATIVE | templates/users/settings/_base.html:4 |
| CrowderSoup__vTodo._base.content | templates/users/settings/_base.html | (extended by a child template) | NATIVE | templates/users/settings/_base.html:6 |
| CrowderSoup__vTodo._base.settings_header | templates/users/settings/_base.html | (extended by a child template) | NATIVE | templates/users/settings/_base.html:8 |
| CrowderSoup__vTodo._base.settings_content | templates/users/settings/_base.html | (extended by a child template) | NATIVE | templates/users/settings/_base.html:35 |
| CrowderSoup__vTodo.dashboard.admin_title | templates/siteadmin/dashboard.html | apps/siteadmin/views.py | NATIVE | templates/siteadmin/dashboard.html:3, apps/siteadmin/views.py |
| CrowderSoup__vTodo.dashboard.admin_content | templates/siteadmin/dashboard.html | apps/siteadmin/views.py | NATIVE | templates/siteadmin/dashboard.html:5, apps/siteadmin/views.py |
| CrowderSoup__vTodo._base.body_class | templates/siteadmin/_base.html | (extended by a child template) | NATIVE | templates/siteadmin/_base.html:3 |
| CrowderSoup__vTodo._base.title | templates/siteadmin/_base.html | (extended by a child template) | NATIVE | templates/siteadmin/_base.html:4 |
| CrowderSoup__vTodo._base.admin_title | templates/siteadmin/_base.html | (extended by a child template) | NATIVE | templates/siteadmin/_base.html:4 |
| CrowderSoup__vTodo._base.content | templates/siteadmin/_base.html | (extended by a child template) | NATIVE | templates/siteadmin/_base.html:6 |
| CrowderSoup__vTodo._base.admin_content | templates/siteadmin/_base.html | (extended by a child template) | NATIVE | templates/siteadmin/_base.html:20 |
| CrowderSoup__vTodo.board.body_class | templates/boards/board.html | apps/users/views.py | NATIVE | templates/boards/board.html:3, apps/users/views.py |
| CrowderSoup__vTodo.board.title | templates/boards/board.html | apps/users/views.py | NATIVE | templates/boards/board.html:4, apps/users/views.py |
| CrowderSoup__vTodo.board.content | templates/boards/board.html | apps/users/views.py | NATIVE | templates/boards/board.html:6, apps/users/views.py |
| CrowderSoup__vTodo.calendar.body_class | templates/calendar/calendar.html | apps/users/views.py | NATIVE | templates/calendar/calendar.html:3, apps/users/views.py |
| CrowderSoup__vTodo.calendar.title | templates/calendar/calendar.html | apps/users/views.py | NATIVE | templates/calendar/calendar.html:4, apps/users/views.py |
| CrowderSoup__vTodo.calendar.content | templates/calendar/calendar.html | apps/users/views.py | NATIVE | templates/calendar/calendar.html:6, apps/users/views.py |

## Data
| Name | Model/Table/Entity | Operations | Fields/Interface | Evidence |
|------|--------------------|------------|------------------|----------|
| teams.Team | Team | READ, WRITE | name, created_at | apps/teams/models.py:8, apps/teams/views.py (write path) |
| teams.TeamMembership | TeamMembership | READ, WRITE | team, user, role, joined_at | apps/teams/models.py:16, apps/teams/views.py (write path) |
| teams.TeamInvite | TeamInvite | READ | team, email, token, invited_by, created_at, expires_at, accepted_at | apps/teams/models.py:37, apps/teams/admin.py (referenced) |
| emailauth.EmailIdentity | EmailIdentity | READ, WRITE | user, email, verified, created_at | apps/emailauth/models.py:5, apps/teams/tests/test_views.py (write path) |
| tasks.TaskStatus | TaskStatus | READ, WRITE | user, team, name, slug, order, color, is_done | apps/tasks/models.py:17, apps/teams/tests/test_views.py (write path) |
| tasks.Task | Task | READ, WRITE | user, team, assignee, title, notes, status, previous_status, order, due_date, due_time, duration_minutes, tags, is_archived, recurrence_days, recurrence_from, created_at, updated_at, completed_at | apps/tasks/models.py:71, apps/teams/tests/test_views.py (write path) |
| tasks.TaskComment | TaskComment | READ, WRITE | task, body, created_at | apps/tasks/models.py:157, apps/boards/views.py (write path) |
| tasks.TaskActivity | TaskActivity | READ, WRITE | task, actor, field, old_value, new_value, created_at | apps/tasks/models.py:169, apps/teams/views.py (write path) |
| siteadmin.SiteSettings | SiteSettings | READ, WRITE | signup_mode | apps/siteadmin/models.py:8, apps/siteadmin/tests/test_selectors.py (write path) |
| siteadmin.SiteInvite | SiteInvite | READ | email, token, invited_by, created_at, expires_at, accepted_at | apps/siteadmin/models.py:32, apps/siteadmin/selectors.py (referenced) |
| integrations.ExternalLink | ExternalLink | READ, WRITE | task, provider, external_id, external_url, synced_at, metadata | apps/integrations/models.py:7, apps/integrations/google_calendar/sync.py (write path) |
| integrations.GoogleCalendarConnection | GoogleCalendarConnection | READ, WRITE | user, calendar_id, refresh_token_encrypted, is_active, created_at, last_synced_at, last_sync_error | apps/integrations/models.py:37, apps/users/tests/test_views.py (write path) |
| boards.Board | Board | READ, WRITE | user, team, name, created_at | apps/boards/models.py:5, apps/teams/views.py (write path) |
| boards.Column | Column | READ, WRITE | board, label, filter_config, order, color | apps/boards/models.py:50, apps/teams/tests/test_views.py (write path) |
| boards.SavedFilter | SavedFilter | READ, WRITE | board, name, filter_config, created_at | apps/boards/models.py:77, apps/boards/tests/test_calendar_views.py (write path) |

## Extension System

(not recorded on the form)

## Adapter Requirements

None. Every attach point above is native to the source.
