# Attach Points

Application: shacker/django-todo
Repository: shacker/django-todo
Commit: 
Framework: django
Datastore: 

## Events
| Name | Source | Symbol | Payload | Implementation | Evidence |
|------|--------|--------|---------|----------------|----------|

## Slots
| Name | Source | Rendering Context | Implementation | Evidence |
|------|--------|-------------------|----------------|----------|
| shacker__django-todo.import_csv.title | todo/templates/todo/import_csv.html | todo/views/import_csv.py | NATIVE | todo/templates/todo/import_csv.html:4, todo/views/import_csv.py |
| shacker__django-todo.import_csv.content | todo/templates/todo/import_csv.html | todo/views/import_csv.py | NATIVE | todo/templates/todo/import_csv.html:6, todo/views/import_csv.py |
| shacker__django-todo.add_list.page_heading | todo/templates/todo/add_list.html | todo/views/add_list.py | NATIVE | todo/templates/todo/add_list.html:2, todo/views/add_list.py |
| shacker__django-todo.add_list.title | todo/templates/todo/add_list.html | todo/views/add_list.py | NATIVE | todo/templates/todo/add_list.html:3, todo/views/add_list.py |
| shacker__django-todo.add_list.content | todo/templates/todo/add_list.html | todo/views/add_list.py | NATIVE | todo/templates/todo/add_list.html:4, todo/views/add_list.py |
| shacker__django-todo.task_detail.title | todo/templates/todo/task_detail.html | todo/views/task_detail.py | NATIVE | todo/templates/todo/task_detail.html:3, todo/views/task_detail.py |
| shacker__django-todo.task_detail.extrahead | todo/templates/todo/task_detail.html | todo/views/task_detail.py | NATIVE | todo/templates/todo/task_detail.html:5, todo/views/task_detail.py |
| shacker__django-todo.task_detail.content | todo/templates/todo/task_detail.html | todo/views/task_detail.py | NATIVE | todo/templates/todo/task_detail.html:21, todo/views/task_detail.py |
| shacker__django-todo.task_detail.extra_js | todo/templates/todo/task_detail.html | todo/views/task_detail.py | NATIVE | todo/templates/todo/task_detail.html:211, todo/views/task_detail.py |
| shacker__django-todo.list_detail.title | todo/templates/todo/list_detail.html | todo/views/list_detail.py | NATIVE | todo/templates/todo/list_detail.html:4, todo/views/list_detail.py |
| shacker__django-todo.list_detail.content | todo/templates/todo/list_detail.html | todo/views/list_detail.py | NATIVE | todo/templates/todo/list_detail.html:6, todo/views/list_detail.py |
| shacker__django-todo.list_detail.extra_js | todo/templates/todo/list_detail.html | todo/views/list_detail.py | NATIVE | todo/templates/todo/list_detail.html:89, todo/views/list_detail.py |
| shacker__django-todo.search_results.title | todo/templates/todo/search_results.html | todo/views/search.py | NATIVE | todo/templates/todo/search_results.html:3, todo/views/search.py |
| shacker__django-todo.search_results.content_title | todo/templates/todo/search_results.html | todo/views/search.py | NATIVE | todo/templates/todo/search_results.html:4, todo/views/search.py |
| shacker__django-todo.search_results.content | todo/templates/todo/search_results.html | todo/views/search.py | NATIVE | todo/templates/todo/search_results.html:6, todo/views/search.py |
| shacker__django-todo.base.extrahead | todo/templates/todo/base.html | (extended by a child template) | NATIVE | todo/templates/todo/base.html:4 |
| shacker__django-todo.add_task_external.page_heading | todo/templates/todo/add_task_external.html | todo/views/external_add.py | NATIVE | todo/templates/todo/add_task_external.html:2, todo/views/external_add.py |
| shacker__django-todo.add_task_external.title | todo/templates/todo/add_task_external.html | todo/views/external_add.py | NATIVE | todo/templates/todo/add_task_external.html:3, todo/views/external_add.py |
| shacker__django-todo.add_task_external.content | todo/templates/todo/add_task_external.html | todo/views/external_add.py | NATIVE | todo/templates/todo/add_task_external.html:5, todo/views/external_add.py |
| shacker__django-todo.list_lists.title | todo/templates/todo/list_lists.html | todo/views/list_lists.py | NATIVE | todo/templates/todo/list_lists.html:3, todo/views/list_lists.py |
| shacker__django-todo.list_lists.content | todo/templates/todo/list_lists.html | todo/views/list_lists.py | NATIVE | todo/templates/todo/list_lists.html:5, todo/views/list_lists.py |
| shacker__django-todo.del_list.title | todo/templates/todo/del_list.html | todo/views/del_list.py | NATIVE | todo/templates/todo/del_list.html:2, todo/views/del_list.py |
| shacker__django-todo.del_list.content | todo/templates/todo/del_list.html | todo/views/del_list.py | NATIVE | todo/templates/todo/del_list.html:4, todo/views/del_list.py |

## Data
| Name | Model/Table/Entity | Operations | Fields/Interface | Evidence |
|------|--------------------|------------|------------------|----------|
| todo.TaskList | TaskList | READ, WRITE | name, slug, group | todo/models.py:55, todo/forms.py (write path) |
| todo.Task | Task | READ, WRITE | title, task_list, created_date, due_date, completed, completed_date, created_by, assigned_to, note, priority | todo/models.py:71, todo/forms.py (write path) |
| todo.Comment | Comment | READ, WRITE | author, task, date, email_from, email_message_id, body | todo/models.py:127, todo/views/task_detail.py (write path) |
| todo.Attachment | Attachment | READ, WRITE | task, added_by, timestamp, file | todo/models.py:166, todo/views/task_detail.py (write path) |

## Extension System

(not recorded on the form)

## Adapter Requirements

None. Every attach point above is native to the source.
