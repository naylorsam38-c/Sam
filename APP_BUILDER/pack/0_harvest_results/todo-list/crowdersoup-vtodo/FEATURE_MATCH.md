# FEATURE_MATCH — CrowderSoup/vTodo

exemplar: Todoist
features checked: 15
features matched (CODE): 8
docs-only: 0
not found: 7
feature_match: 0.53

| Feature | Verdict | Keyword | Evidence |
|---------|---------|---------|----------|
| recurring tasks | MATCHED | recurrence | apps/tasks/models.py:129 ('spawn_recurrence') |
| labels | MATCHED | label | apps/users/views.py:88 ('_saved_filters_with_labels') |
| custom filters | MATCHED | filter | apps/teams/admin.py:21 ('list_filter') |
| reminders | NOT_FOUND | - | - |
| sub-tasks | NOT_FOUND | - | - |
| sections | NOT_FOUND | - | - |
| karma productivity tracking | NOT_FOUND | - | - |
| shared projects | MATCHED | share | apps/teams/tests/test_views.py:40 ('test_team_create_creates_shared_team_board') |
| task assignment | MATCHED | assign | apps/teams/tests/test_views.py:227 ('test_member_remove_unassigns_the_removed_user_from_team_tasks') |
| task priorities | NOT_FOUND | - | - |
| board (kanban) view | MATCHED | board | config/urls.py:13 ('board/') |
| project templates | NOT_FOUND | - | - |
| natural language quick add | NOT_FOUND | - | - |
| calendar integration | MATCHED | calendar | config/urls.py:14 ('calendar/') |
| task comments and file attachments | MATCHED | comment | apps/tasks/models.py:155 ('TaskComment') |
