# Attach Points

Application: iyanuashiri/meethub
Repository: iyanuashiri/meethub
Commit: 
Framework: django
Datastore: postgresql

## Events
| Name | Source | Symbol | Payload | Implementation | Evidence |
|------|--------|--------|---------|----------------|----------|

## Slots
| Name | Source | Rendering Context | Implementation | Evidence |
|------|--------|-------------------|----------------|----------|
| iyanuashiri__meethub.notifications.content | meethub/actions/templates/actions/notifications.html | meethub/actions/views.py | NATIVE | meethub/actions/templates/actions/notifications.html:5, meethub/actions/views.py |
| iyanuashiri__meethub.profile_detail.content | meethub/profile/templates/profile/profile_detail.html | meethub/profile/views.py | NATIVE | meethub/profile/templates/profile/profile_detail.html:5, meethub/profile/views.py |
| iyanuashiri__meethub.update_form.content | meethub/profile/templates/profile/update_form.html | meethub/profile/views.py | NATIVE | meethub/profile/templates/profile/update_form.html:6, meethub/profile/views.py |
| iyanuashiri__meethub.create_form.title | meethub/events/templates/events/create_form.html | meethub/events/views.py | NATIVE | meethub/events/templates/events/create_form.html:5, meethub/events/views.py |
| iyanuashiri__meethub.create_form.content | meethub/events/templates/events/create_form.html | meethub/events/views.py | NATIVE | meethub/events/templates/events/create_form.html:7, meethub/events/views.py |
| iyanuashiri__meethub.update_form.title | meethub/events/templates/events/update_form.html | meethub/profile/views.py | NATIVE | meethub/events/templates/events/update_form.html:5, meethub/profile/views.py |
| iyanuashiri__meethub.update_form.content | meethub/events/templates/events/update_form.html | meethub/profile/views.py | NATIVE | meethub/events/templates/events/update_form.html:7, meethub/profile/views.py |
| iyanuashiri__meethub.delete.title | meethub/events/templates/events/delete.html | meethub/events/views.py | NATIVE | meethub/events/templates/events/delete.html:3, meethub/events/views.py |
| iyanuashiri__meethub.delete.content | meethub/events/templates/events/delete.html | meethub/events/views.py | NATIVE | meethub/events/templates/events/delete.html:5, meethub/events/views.py |
| iyanuashiri__meethub.list_of_events.title | meethub/events/templates/events/list_of_events.html | meethub/events/views.py | NATIVE | meethub/events/templates/events/list_of_events.html:4, meethub/events/views.py |
| iyanuashiri__meethub.list_of_events.content | meethub/events/templates/events/list_of_events.html | meethub/events/views.py | NATIVE | meethub/events/templates/events/list_of_events.html:6, meethub/events/views.py |
| iyanuashiri__meethub.detail.title | meethub/events/templates/events/detail.html | meethub/profile/views.py | NATIVE | meethub/events/templates/events/detail.html:7, meethub/profile/views.py |
| iyanuashiri__meethub.detail.content | meethub/events/templates/events/detail.html | meethub/profile/views.py | NATIVE | meethub/events/templates/events/detail.html:9, meethub/profile/views.py |
| iyanuashiri__meethub.base.title | meethub/events/templates/events/base.html | (extended by a child template) | NATIVE | meethub/events/templates/events/base.html:17 |
| iyanuashiri__meethub.base.content | meethub/events/templates/events/base.html | (extended by a child template) | NATIVE | meethub/events/templates/events/base.html:289 |
| iyanuashiri__meethub.delete.content | meethub/comments/templates/comments/delete.html | meethub/events/views.py | NATIVE | meethub/comments/templates/comments/delete.html:3, meethub/events/views.py |
| iyanuashiri__meethub.detail.content | meethub/comments/templates/comments/detail.html | meethub/profile/views.py | NATIVE | meethub/comments/templates/comments/detail.html:5, meethub/profile/views.py |
| iyanuashiri__meethub.base1.title | meethub/accounts/templates/registration/base1.html | (extended by a child template) | NATIVE | meethub/accounts/templates/registration/base1.html:15 |
| iyanuashiri__meethub.base1.content | meethub/accounts/templates/registration/base1.html | (extended by a child template) | NATIVE | meethub/accounts/templates/registration/base1.html:262 |
| iyanuashiri__meethub.signup.title | meethub/accounts/templates/registration/signup.html | meethub/accounts/views.py | NATIVE | meethub/accounts/templates/registration/signup.html:4, meethub/accounts/views.py |
| iyanuashiri__meethub.signup.content | meethub/accounts/templates/registration/signup.html | meethub/accounts/views.py | NATIVE | meethub/accounts/templates/registration/signup.html:6, meethub/accounts/views.py |
| iyanuashiri__meethub.homepage.title | meethub/accounts/templates/registration/homepage.html | meethub/accounts/views.py | NATIVE | meethub/accounts/templates/registration/homepage.html:3, meethub/accounts/views.py |
| iyanuashiri__meethub.homepage.content | meethub/accounts/templates/registration/homepage.html | meethub/accounts/views.py | NATIVE | meethub/accounts/templates/registration/homepage.html:5, meethub/accounts/views.py |

## Data
| Name | Model/Table/Entity | Operations | Fields/Interface | Evidence |
|------|--------------------|------------|------------------|----------|
| actions.Action | Action | READ, WRITE | user, verb, created, target_ct, target_id | meethub/actions/models.py:11, meethub/actions/tests/test_models.py (write path) |
| profile.Profile | Profile | READ, WRITE | user, date_of_birth, photo | meethub/profile/models.py:12, meethub/profile/forms.py (write path) |
| events.Category | Category | READ, WRITE | name, description | meethub/events/models.py:14, meethub/events/tests/test_forms.py (write path) |
| events.Event | Event | READ, WRITE | name, details, venue, date, time, category, creator, attendees, num_of_attendees | meethub/events/models.py:26, meethub/events/forms.py (write path) |
| comments.Comment | Comment | READ, WRITE | comment, created_date, created_time, event, created_by, parent | meethub/comments/models.py:10, meethub/events/tests/test_views.py (write path) |

## Extension System

(not recorded on the form)

## Adapter Requirements

None. Every attach point above is native to the source.
