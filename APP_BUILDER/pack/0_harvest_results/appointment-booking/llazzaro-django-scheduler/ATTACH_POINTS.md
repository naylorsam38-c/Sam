# Attach Points

Application: llazzaro/django-scheduler
Repository: llazzaro/django-scheduler
Commit: 
Framework: django
Datastore: 

## Events
| Name | Source | Symbol | Payload | Implementation | Evidence |
|------|--------|--------|---------|----------------|----------|

## Slots
| Name | Source | Rendering Context | Implementation | Evidence |
|------|--------|-------------------|----------------|----------|
| llazzaro__django-scheduler.fullcalendar.head_title | schedule/templates/fullcalendar.html | schedule/views.py | NATIVE | schedule/templates/fullcalendar.html:4, schedule/views.py |
| llazzaro__django-scheduler.fullcalendar.tab_id | schedule/templates/fullcalendar.html | schedule/views.py | NATIVE | schedule/templates/fullcalendar.html:5, schedule/views.py |
| llazzaro__django-scheduler.fullcalendar.extra_head | schedule/templates/fullcalendar.html | schedule/views.py | NATIVE | schedule/templates/fullcalendar.html:6, schedule/views.py |
| llazzaro__django-scheduler.fullcalendar.body | schedule/templates/fullcalendar.html | schedule/views.py | NATIVE | schedule/templates/fullcalendar.html:10, schedule/views.py |
| llazzaro__django-scheduler.base.head_title | schedule/templates/base.html | (extended by a child template) | NATIVE | schedule/templates/base.html:6 |
| llazzaro__django-scheduler.base.extra_head | schedule/templates/base.html | (extended by a child template) | NATIVE | schedule/templates/base.html:12 |
| llazzaro__django-scheduler.base.body | schedule/templates/base.html | (extended by a child template) | NATIVE | schedule/templates/base.html:29 |
| llazzaro__django-scheduler.base.footer | schedule/templates/base.html | (extended by a child template) | NATIVE | schedule/templates/base.html:34 |
| llazzaro__django-scheduler.calendar_month.body | schedule/templates/schedule/calendar_month.html | schedule/urls.py | NATIVE | schedule/templates/schedule/calendar_month.html:4, schedule/urls.py |
| llazzaro__django-scheduler.create_event.body | schedule/templates/schedule/create_event.html | schedule/views.py | NATIVE | schedule/templates/schedule/create_event.html:4, schedule/views.py |
| llazzaro__django-scheduler.calendar_tri_month.body | schedule/templates/schedule/calendar_tri_month.html | schedule/urls.py | NATIVE | schedule/templates/schedule/calendar_tri_month.html:3, schedule/urls.py |
| llazzaro__django-scheduler.delete_event.body | schedule/templates/schedule/delete_event.html | schedule/views.py | NATIVE | schedule/templates/schedule/delete_event.html:4, schedule/views.py |
| llazzaro__django-scheduler.calendar.body | schedule/templates/schedule/calendar.html | schedule/views.py | NATIVE | schedule/templates/schedule/calendar.html:5, schedule/views.py |
| llazzaro__django-scheduler.calendar_year.body | schedule/templates/schedule/calendar_year.html | schedule/urls.py | NATIVE | schedule/templates/schedule/calendar_year.html:3, schedule/urls.py |
| llazzaro__django-scheduler.occurrence.body | schedule/templates/schedule/occurrence.html | schedule/views.py | NATIVE | schedule/templates/schedule/occurrence.html:4, schedule/views.py |
| llazzaro__django-scheduler.calendar_day.body | schedule/templates/schedule/calendar_day.html | schedule/urls.py | NATIVE | schedule/templates/schedule/calendar_day.html:4, schedule/urls.py |
| llazzaro__django-scheduler.edit_occurrence.body | schedule/templates/schedule/edit_occurrence.html | schedule/views.py | NATIVE | schedule/templates/schedule/edit_occurrence.html:4, schedule/views.py |
| llazzaro__django-scheduler.calendar_week.body | schedule/templates/schedule/calendar_week.html | schedule/urls.py | NATIVE | schedule/templates/schedule/calendar_week.html:4, schedule/urls.py |
| llazzaro__django-scheduler.cancel_occurrence.body | schedule/templates/schedule/cancel_occurrence.html | schedule/views.py | NATIVE | schedule/templates/schedule/cancel_occurrence.html:4, schedule/views.py |
| llazzaro__django-scheduler.calendar_compact_month.body | schedule/templates/schedule/calendar_compact_month.html | schedule/urls.py | NATIVE | schedule/templates/schedule/calendar_compact_month.html:3, schedule/urls.py |
| llazzaro__django-scheduler.event.body | schedule/templates/schedule/event.html | schedule/views.py | NATIVE | schedule/templates/schedule/event.html:4, schedule/views.py |

## Data
| Name | Model/Table/Entity | Operations | Fields/Interface | Evidence |
|------|--------------------|------------|------------------|----------|
| schedule.Rule | Rule | READ, WRITE | name, description, frequency, params | schedule/models/rules.py:31, tests/test_periods.py (write path) |
| schedule.Calendar | Calendar | READ, WRITE | name, slug | schedule/models/calendars.py:106, tests/test_perms.py (write path) |
| schedule.CalendarRelation | CalendarRelation | READ | calendar, content_type, object_id, distinction, inheritable | schedule/models/calendars.py:197, tests/test_calendar.py (referenced) |
| schedule.Event | Event | READ, WRITE | start, end, title, description, creator, created_on, updated_on, rule, end_recurring_period, calendar, color_event | schedule/models/events.py:47, tests/test_perms.py (write path) |
| schedule.EventRelation | EventRelation | READ | event, content_type, object_id, distinction | schedule/models/events.py:544, tests/test_event.py (referenced) |
| schedule.Occurrence | Occurrence | READ, WRITE | event, title, description, start, end, cancelled, original_start, original_end, created_on, updated_on | schedule/models/events.py:582, tests/test_perms.py (write path) |

## Extension System

(not recorded on the form)

## Adapter Requirements

None. Every attach point above is native to the source.
