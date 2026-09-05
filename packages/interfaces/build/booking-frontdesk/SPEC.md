# Front Desk (booking-frontdesk)

`SPEC-BOOKING-FRONTDESK-REF` — assembled from `booking-frontdesk` against graph 3.0. Every field below is numbered by the question, default, or derivation that owns it — nothing here was guessed.

## actions

| # | Field | Value | Source |
|---|---|---|---|
| Z.02 | `actions.inventory` | confirmed | question |
| D12 | `actions.inventory.items` | see build_model.D12 | derivation |

## api

| # | Field | Value | Source |
|---|---|---|---|
| sys_api_convention | `api.*` | One fixed REST convention for every endpoint, verb and envelope. | system_default |

## auth

| # | Field | Value | Source |
|---|---|---|---|
| sys_first_admin | `auth.bootstrap_admin` | The first super-role account is seeded from the deploy inputs, not created throu… | system_default |
| AU.05 | `auth.default_role` | null | question |
| AU.12 | `auth.deletion_allowed` | {"allowed": "yes", "by": "both", "data": "anonymised"} | question |
| AU.12 | `auth.deletion_by` | {"allowed": "yes", "by": "both", "data": "anonymised"} | question |
| AU.12 | `auth.deletion_data_policy` | {"allowed": "yes", "by": "both", "data": "anonymised"} | question |
| AU.03 | `auth.email_verification` | yes | question |
| sys_account_identity | `auth.identity_field` | The email address is the account identity; changing it requires re-verification. | system_default |
| AU.06 | `auth.invite_authority` | {"inviters": ["Owner"], "default_role": "Staff"} | question |
| AU.06 | `auth.invite_default_role` | {"inviters": ["Owner"], "default_role": "Staff"} | question |
| sys_invite_expiry | `auth.invite_expiry` | Invitations expire after 7 days and can be re-sent. | system_default |
| AU.08 | `auth.lockout_attempts` | {"attempts": 5, "duration": "15 minutes"} | question |
| AU.08 | `auth.lockout_duration` | {"attempts": 5, "duration": "15 minutes"} | question |
| AU.04 | `auth.methods` | ["password", "google"] | question |
| AU.07 | `auth.mfa_method` | {"scope": "nobody", "method": "n/a"} | question |
| sys_mfa_recovery | `auth.mfa_recovery` | One-time recovery codes issued at MFA enrolment. | system_default |
| AU.07 | `auth.mfa_scope` | {"scope": "nobody", "method": "n/a"} | question |
| AU.09 | `auth.multi_device` | yes | question |
| sys_profile_self_edit | `auth.profile_self_service` | Every user can edit their own name, email, password and notification preferences… | system_default |
| AU.02 | `auth.registration_fields` | [{"name": "Full name", "type": "short_text", "required": "yes", "unique": "no"},… | question |
| AU.01 | `auth.registration_modes` | ["invited"] | question |
| A.07 | `auth.required` | yes | question |
| AU.13 | `auth.reset_others_by` | ["super"] | question |
| sys_password_reset | `auth.self_reset_flow` | Self-service reset by emailed link, valid 1 hour. | system_default |
| AU.10 | `auth.session_length` | 30 days | question |
| sys_suspended_experience | `auth.suspended_screen` | A suspended user sees a fixed 'account suspended — contact <support contact>' sc… | system_default |
| AU.11 | `auth.suspension_allowed` | {"allowed": "yes", "by": ["super"], "auto_triggers": []} | question |
| AU.11 | `auth.suspension_auto_triggers` | {"allowed": "yes", "by": ["super"], "auto_triggers": []} | question |
| AU.11 | `auth.suspension_by` | {"allowed": "yes", "by": ["super"], "auto_triggers": []} | question |

## billing

| # | Field | Value | Source |
|---|---|---|---|
| B.10 | `billing.cancellation` | null | question |
| B.02 | `billing.charged_party` | person | question |
| B.04 | `billing.currency` | AUD | question |
| sys_billing_details | `billing.details_collection` | Card, billing address and tax IDs are collected by the gateway's hosted form; in… | system_default |
| sys_billing_details | `billing.invoices` | Card, billing address and tax IDs are collected by the gateway's hosted form; in… | system_default |
| B.01 | `billing.model` | ["one_off"] | question |
| B.08 | `billing.on_failure` | {"grace_days": 0, "after_repeated": "cancel"} | question |
| sys_limit_reached | `billing.on_limit_reached` | Hitting a plan limit shows an upgrade prompt, then blocks the action. | system_default |
| B.07 | `billing.payment_methods` | card_only | question |
| B.09 | `billing.plan_change` | null | question |
| D10 | `billing.plan_linkage` | see build_model.D10 | derivation |
| B.03 | `billing.plans` | [{"name": "Per appointment", "price": "the Service's own Price", "interval": "on… | question |
| sys_proration | `billing.proration_rule` | Mid-cycle plan changes are prorated by the gateway. | system_default |
| B.11 | `billing.refunds` | {"allowed": "yes", "by": ["Owner"]} | question |
| A.09 | `billing.required` | yes | question |
| sys_tax_calculation | `billing.tax_calculation` | Tax computed by the payment gateway from the billing address. | system_default |
| B.05 | `billing.trial` | null | question |
| B.06 | `billing.usage_charge_timing` | null | question |
| B.06 | `billing.usage_unit` | null | question |
| sys_idempotency_webhook | `billing.webhook_handling` | Payment webhooks signature-verified and processed exactly once. | system_default |

## client

| # | Field | Value | Source |
|---|---|---|---|
| C.06 | `client.landing_screen_per_role` | {"Owner": "Calendar", "Staff": "Calendar"} | question |
| C.05 | `client.mobile_behaviour` | {"mode": "different", "what": "the public booking flow is mobile-first: one step… | question |
| C.07 | `client.navigation` | confirmed | question |
| D13 | `client.navigation.derived` | see build_model.D13 | derivation |
| A.06 | `client.platforms` | ["web"] | question |
| A.10 | `client.public_surfaces` | ["public booking page", "public booking form"] | question |

## data

| # | Field | Value | Source |
|---|---|---|---|
| A.12 | `data.import_required` | {"required": "no"} | question |
| A.12 | `data.import_sources` | {"required": "no"} | question |

## deploy

| # | Field | Value | Source |
|---|---|---|---|
| DI.10 | `deploy.app_store_accounts` | [PENDING — collected at deploy time, not at requirements time] | deploy_input |
| DI.01 | `deploy.domain` | [PENDING — collected at deploy time, not at requirements time] | deploy_input |
| DI.02 | `deploy.email_sender` | [PENDING — collected at deploy time, not at requirements time] | deploy_input |
| DI.04 | `deploy.first_admin_email` | [PENDING — collected at deploy time, not at requirements time] | deploy_input |
| DI.06 | `deploy.gateway_credentials` | [PENDING — collected at deploy time, not at requirements time] | deploy_input |
| DI.09 | `deploy.integration_credentials` | [PENDING — collected at deploy time, not at requirements time] | deploy_input |
| DI.11 | `deploy.legal_documents` | [PENDING — collected at deploy time, not at requirements time] | deploy_input |
| DI.08 | `deploy.oauth_credentials` | [PENDING — collected at deploy time, not at requirements time] | deploy_input |
| DI.05 | `deploy.region` | [PENDING — collected at deploy time, not at requirements time] | deploy_input |
| DI.07 | `deploy.sms_credentials` | [PENDING — collected at deploy time, not at requirements time] | deploy_input |
| DI.03 | `deploy.support_contact` | [PENDING — collected at deploy time, not at requirements time] | deploy_input |

## deviation

| # | Field | Value | Source |
|---|---|---|---|
| A.14 | `deviation.flags` | [] | question |

## engine

| # | Field | Value | Source |
|---|---|---|---|
| 0.01 | `engine.involvement` | guided | question |

## file

| # | Field | Value | Source |
|---|---|---|---|
| sys_file_type_inference | `file.*.allowed_mimes` | Allowed formats come from a fixed allow-list per file category. | system_default |
| sys_image_handling | `file.*.image_handling` | Images get thumbnails; downloads are served by signed URL. | system_default |
| sys_file_security_scanning | `file.*.malware_scanning` | Async malware scan before a file is marked active. | system_default |
| D06 | `file.*.retention` | see build_model.D06 | derivation |
| sys_file_storage | `file.*.storage_backend` | Private object storage for uploads. | system_default |

## form

| # | Field | Value | Source |
|---|---|---|---|
| D02 | `form.*.fields` | see build_model.D02 | derivation |
| sys_form_failure | `form.*.layout` | A failed submit shows inline errors and keeps what was typed; forms are single-p… | system_default |
| sys_form_failure | `form.*.on_failure` | A failed submit shows inline errors and keeps what was typed; forms are single-p… | system_default |
| sys_form_failure | `form.*.spam_protection` | A failed submit shows inline errors and keeps what was typed; forms are single-p… | system_default |
| F.03:Public booking form | `form.Public booking form.conditional_fields` | [] | question |
| F.04:Public booking form | `form.Public booking form.draft_save` | no | question |
| F.02:Public booking form | `form.Public booking form.extra_fields` | {"target": "Appointment", "extra_fields": []} | question |
| F.01:Public booking form | `form.Public booking form.fillers` | {"purpose": "lets a customer pick a service, a time and a staff member and book … | question |
| F.05:Public booking form | `form.Public booking form.on_success` | stay_with_message | question |
| F.01:Public booking form | `form.Public booking form.purpose` | {"purpose": "lets a customer pick a service, a time and a staff member and book … | question |
| F.02:Public booking form | `form.Public booking form.target_record` | {"target": "Appointment", "extra_fields": []} | question |

## integration

| # | Field | Value | Source |
|---|---|---|---|
| sys_retry_policy | `integration.*.retry_policy` | Failed external calls retry 3× with exponential backoff + jitter. | system_default |
| A.11 | `integration.public_api_required` | no | question |

## inventory

| # | Field | Value | Source |
|---|---|---|---|
| A.15 | `inventory.file_types` | [] | question |
| A.15 | `inventory.forms` | ["Public booking form"] | question |
| A.15 | `inventory.integrations` | [] | question |
| A.15 | `inventory.notifications` | ["Booking confirmation", "Appointment reminder", "Cancellation notice"] | question |
| A.15 | `inventory.records` | ["Service", "Customer", "Appointment"] | question |
| A.15 | `inventory.reports` | ["Upcoming appointments", "No-show rate"] | question |
| A.15 | `inventory.roles` | ["Owner", "Staff"] | question |
| A.15 | `inventory.screens` | [] | question |
| A.15 | `inventory.workflows` | ["Appointment lifecycle"] | question |

## legal

| # | Field | Value | Source |
|---|---|---|---|
| AU.14 | `legal.terms_required` | {"required": "yes", "status": "need_drafting"} | question |
| AU.14 | `legal.terms_status` | {"required": "yes", "status": "need_drafting"} | question |

## locale

| # | Field | Value | Source |
|---|---|---|---|
| sys_locale_formatting | `locale.formatting` | Dates, numbers and currency display in the format of A.13's region; stored in UT… | system_default |
| A.13 | `locale.languages` | {"region": "Australia", "languages": ["English"]} | question |
| A.13 | `locale.primary_region` | {"region": "Australia", "languages": ["English"]} | question |
| sys_locale_formatting | `locale.timezone_handling` | Dates, numbers and currency display in the format of A.13's region; stored in UT… | system_default |

## notification

| # | Field | Value | Source |
|---|---|---|---|
| sys_notification_copywriting | `notification.*.copy_final` | Message wording drafted at build time and approved by the owner before launch; n… | system_default |
| sys_notification_retry | `notification.*.retry_policy` | 3 delivery retries then dead-letter. | system_default |
| D05 | `notification.*.timing` | see build_model.D05 | derivation |
| N.03:Appointment reminder | `notification.Appointment reminder.channels` | ["email", "sms"] | question |
| N.04:Appointment reminder | `notification.Appointment reminder.intent` | Your appointment is tomorrow — reply or use the link to reschedule. | question |
| N.05:Appointment reminder | `notification.Appointment reminder.opt_out` | yes | question |
| N.02:Appointment reminder | `notification.Appointment reminder.recipients` | [{"kind": "field", "record": "Appointment", "field": "Customer"}] | question |
| N.01:Appointment reminder | `notification.Appointment reminder.trigger` | {"kind": "relative_to_date", "record": "Appointment", "date_field": "Start", "of… | question |
| N.03:Booking confirmation | `notification.Booking confirmation.channels` | ["email", "sms"] | question |
| N.04:Booking confirmation | `notification.Booking confirmation.intent` | Your booking is locked in — here's the time, the service and how to change it. | question |
| N.05:Booking confirmation | `notification.Booking confirmation.opt_out` | no | question |
| N.02:Booking confirmation | `notification.Booking confirmation.recipients` | [{"kind": "field", "record": "Appointment", "field": "Customer"}] | question |
| N.01:Booking confirmation | `notification.Booking confirmation.trigger` | {"kind": "event", "event": "an appointment reaches stage Confirmed"} | question |
| N.03:Cancellation notice | `notification.Cancellation notice.channels` | ["email"] | question |
| N.04:Cancellation notice | `notification.Cancellation notice.intent` | This booking was cancelled — rebook if it wasn't you. | question |
| N.05:Cancellation notice | `notification.Cancellation notice.opt_out` | no | question |
| N.02:Cancellation notice | `notification.Cancellation notice.recipients` | [{"kind": "field", "record": "Appointment", "field": "Customer"}, {"kind": "fiel… | question |
| N.01:Cancellation notice | `notification.Cancellation notice.trigger` | {"kind": "event", "event": "an appointment moves to Cancelled"} | question |

## notify

| # | Field | Value | Source |
|---|---|---|---|
| sys_inapp_inbox | `notify.inbox` | If any notification uses in-app, the app has one notification inbox with read/un… | system_default |

## ops

| # | Field | Value | Source |
|---|---|---|---|
| Z.01 | `ops.recurring_operations` | confirmed | question |
| D11 | `ops.recurring_operations.items` | see build_model.D11 | derivation |

## product

| # | Field | Value | Source |
|---|---|---|---|
| A.03 | `product.audience` | A small service business: an owner and the staff who deliver the appointments. | question |
| A.01 | `product.description` | A front desk for appointments: services with durations and prices, customers, an… | question |
| A.02 | `product.goals` | Take bookings without phone calls, keep the calendar full, and know the no-show … | question |
| A.05 | `product.name` | Front Desk | question |
| A.04 | `product.success_definition` | The book is full a week out and no-shows are rare. | question |

## qa

| # | Field | Value | Source |
|---|---|---|---|
| D15 | `qa.generated_tests` | see build_model.D15 | derivation |
| sys_qa_pass_conditions | `qa.pass_condition.*` | Every node's pass/fail check is generated from that node's own answers. | system_default |

## record

| # | Field | Value | Source |
|---|---|---|---|
| sys_audit_fields | `record.*.audit_fields` | created_at/updated_at/created_by/updated_by on every table. | system_default |
| sys_concurrent_edit | `record.*.concurrency` | Last save wins; a user saving over a newer version is warned and shown the newer… | system_default |
| sys_list_behaviour | `record.*.exportable` | Every record list is searchable and filterable on its visible fields, sorted new… | system_default |
| D01 | `record.*.field.*.storage_type` | see build_model.D01 | derivation |
| D14 | `record.*.field.*.storage_type_for_options` | see build_model.D14 | derivation |
| sys_field_type_defaults | `record.*.field.*.validation` | Each field type carries one standard validation rule and error message. | system_default |
| sys_database_identifiers | `record.*.id_strategy` | UUIDv4 primary keys on every table. | system_default |
| sys_list_behaviour | `record.*.list_behaviour` | Every record list is searchable and filterable on its visible fields, sorted new… | system_default |
| R.06:Appointment | `record.Appointment.access.create` | ["Staff", "public"] | question |
| R.08:Appointment | `record.Appointment.access.delete` | [{"role": "Owner", "scope": "all"}] | question |
| R.07:Appointment | `record.Appointment.access.edit` | [{"role": "Staff", "scope": "all"}] | question |
| R.05:Appointment | `record.Appointment.access.view` | [{"role": "Staff", "scope": "all"}] | question |
| R.13:Appointment | `record.Appointment.archivable` | yes | question |
| R.15:Appointment | `record.Appointment.custom_actions` | [] | question |
| R.02:Appointment | `record.Appointment.fields` | [{"name": "Service", "type": "link", "required": "yes", "unique": "no", "target_… | question |
| R.10:Appointment | `record.Appointment.has_lifecycle` | {"has": "yes", "stages": ["Booked", "Confirmed", "Completed", "Cancelled", "No-s… | question |
| R.04:Appointment | `record.Appointment.human_id` | {"needed": "yes", "format": "APT-#### (sequential)"} | question |
| R.12:Appointment | `record.Appointment.on_delete` | block | question |
| R.09:Appointment | `record.Appointment.ownership_rule` | null | question |
| R.01:Appointment | `record.Appointment.purpose` | A booked time slot for one customer, one service and one staff member. | question |
| R.11:Appointment | `record.Appointment.relations` | [{"target": "Service", "cardinality": "one_to_many", "required": "yes"}, {"targe… | question |
| R.14:Appointment | `record.Appointment.retention` | forever | question |
| R.03:Appointment | `record.Appointment.title_field` | Start | question |
| R.06:Customer | `record.Customer.access.create` | ["Staff", "public"] | question |
| R.08:Customer | `record.Customer.access.delete` | [{"role": "Owner", "scope": "all"}] | question |
| R.07:Customer | `record.Customer.access.edit` | [{"role": "Staff", "scope": "all"}] | question |
| R.05:Customer | `record.Customer.access.view` | [{"role": "Staff", "scope": "all"}] | question |
| R.13:Customer | `record.Customer.archivable` | yes | question |
| R.15:Customer | `record.Customer.custom_actions` | [] | question |
| R.02:Customer | `record.Customer.fields` | [{"name": "Full name", "type": "short_text", "required": "yes", "unique": "no"},… | question |
| R.10:Customer | `record.Customer.has_lifecycle` | {"has": "no"} | question |
| R.04:Customer | `record.Customer.human_id` | {"needed": "no"} | question |
| R.12:Customer | `record.Customer.on_delete` | null | question |
| R.09:Customer | `record.Customer.ownership_rule` | null | question |
| R.01:Customer | `record.Customer.purpose` | A person who books appointments; created from the public booking form. | question |
| R.11:Customer | `record.Customer.relations` | [] | question |
| R.14:Customer | `record.Customer.retention` | forever | question |
| R.03:Customer | `record.Customer.title_field` | Full name | question |
| R.06:Service | `record.Service.access.create` | ["Owner"] | question |
| R.08:Service | `record.Service.access.delete` | [{"role": "Owner", "scope": "all"}] | question |
| R.07:Service | `record.Service.access.edit` | [{"role": "Owner", "scope": "all"}] | question |
| R.05:Service | `record.Service.access.view` | [{"role": "Staff", "scope": "all"}, {"role": "public", "scope": "public"}] | question |
| R.13:Service | `record.Service.archivable` | yes | question |
| R.15:Service | `record.Service.custom_actions` | [] | question |
| R.02:Service | `record.Service.fields` | [{"name": "Name", "type": "short_text", "required": "yes", "unique": "no"}, {"na… | question |
| R.10:Service | `record.Service.has_lifecycle` | {"has": "no"} | question |
| R.04:Service | `record.Service.human_id` | {"needed": "no"} | question |
| R.12:Service | `record.Service.on_delete` | null | question |
| R.09:Service | `record.Service.ownership_rule` | null | question |
| R.01:Service | `record.Service.purpose` | Something customers can book: a name, a length and a price. | question |
| R.11:Service | `record.Service.relations` | [] | question |
| R.14:Service | `record.Service.retention` | forever | question |
| R.03:Service | `record.Service.title_field` | Name | question |

## report

| # | Field | Value | Source |
|---|---|---|---|
| sys_report_caching | `report.*.cache_policy` | Reports regenerate on demand, cached 5 min. | system_default |
| D07 | `report.*.data_source` | see build_model.D07 | derivation |
| D07 | `report.*.metric.*.derived_definition` | see build_model.D07 | derivation |
| RP.06:No-show rate | `report.No-show rate.default_range` | {"filters": ["Staff member", "Service"], "default_range": "last 30 days"} | question |
| RP.07:No-show rate | `report.No-show rate.export` | {"allowed": "yes", "by": ["Owner"]} | question |
| RP.06:No-show rate | `report.No-show rate.filters` | {"filters": ["Staff member", "Service"], "default_range": "last 30 days"} | question |
| RP.03:No-show rate | `report.No-show rate.form` | {"delivery": "screen", "shape": "both"} | question |
| RP.05:No-show rate:no-show rate | `report.No-show rate.metric.no-show rate.definition` | appointments that ended No-show divided by appointments that ended Completed or … | question |
| RP.04:No-show rate | `report.No-show rate.metrics` | ["no-show rate"] | question |
| RP.01:No-show rate | `report.No-show rate.question` | How often do customers fail to turn up? | question |
| RP.08:No-show rate | `report.No-show rate.scheduled_delivery` | {"enabled": "no"} | question |
| RP.02:No-show rate | `report.No-show rate.viewers` | ["Owner"] | question |
| RP.06:Upcoming appointments | `report.Upcoming appointments.default_range` | {"filters": ["Staff member", "Service"], "default_range": "next 7 days"} | question |
| RP.07:Upcoming appointments | `report.Upcoming appointments.export` | {"allowed": "yes", "by": ["Staff"]} | question |
| RP.06:Upcoming appointments | `report.Upcoming appointments.filters` | {"filters": ["Staff member", "Service"], "default_range": "next 7 days"} | question |
| RP.03:Upcoming appointments | `report.Upcoming appointments.form` | {"delivery": "screen", "shape": "table"} | question |
| RP.04:Upcoming appointments | `report.Upcoming appointments.metrics` | ["count of Appointments in stage Booked or Confirmed"] | question |
| RP.01:Upcoming appointments | `report.Upcoming appointments.question` | What's booked for the coming days, per staff member? | question |
| RP.08:Upcoming appointments | `report.Upcoming appointments.scheduled_delivery` | {"enabled": "no"} | question |
| RP.02:Upcoming appointments | `report.Upcoming appointments.viewers` | ["Staff"] | question |

## role

| # | Field | Value | Source |
|---|---|---|---|
| D04 | `role.*.forbidden_actions` | see build_model.D04 | derivation |
| D04 | `role.*.is_admin` | see build_model.D04 | derivation |
| D04 | `role.*.permitted_actions` | see build_model.D04 | derivation |
| D03 | `role.*.visible_screens` | see build_model.D03 | derivation |
| P.04:Owner | `role.Owner.assignable_by` | null | question |
| P.03:Owner | `role.Owner.billing_access` | null | question |
| P.01:Owner | `role.Owner.description` | null | question |
| P.02:Owner | `role.Owner.sees_private_data` | null | question |
| P.04:Staff | `role.Staff.assignable_by` | ["Owner"] | question |
| P.03:Staff | `role.Staff.billing_access` | no | question |
| P.01:Staff | `role.Staff.description` | A person who delivers services and manages their own calendar. | question |
| P.02:Staff | `role.Staff.sees_private_data` | no | question |

## roles

| # | Field | Value | Source |
|---|---|---|---|
| P.00 | `roles.multi_role_per_person` | no | question |
| A.16 | `roles.super_role` | Owner | question |

## screen

| # | Field | Value | Source |
|---|---|---|---|
| D03 | `screen.*.access` | see build_model.D03 | derivation |
| D03 | `screen.*.contents` | see build_model.D03 | derivation |
| sys_screen_interaction_pattern | `screen.*.interaction_states` | Standard loading / empty / error / success / back / leave-and-return behaviour o… | system_default |

## screens

| # | Field | Value | Source |
|---|---|---|---|
| Z.03 | `screens.inventory` | confirmed | question |
| D13 | `screens.inventory.items` | see build_model.D13 | derivation |

## tenancy

| # | Field | Value | Source |
|---|---|---|---|
| T.07 | `tenancy.branding` | null | question |
| T.02 | `tenancy.creation` | null | question |
| T.06 | `tenancy.isolation` | null | question |
| sys_client_isolation | `tenancy.isolation_mechanism` | Row-level security enforces organisation isolation in the database. | system_default |
| A.08 | `tenancy.mode` | single | question |
| T.01 | `tenancy.multi_membership` | null | question |
| T.05 | `tenancy.operator_role` | null | question |
| T.03 | `tenancy.org_admin_role` | null | question |
| sys_org_switcher | `tenancy.org_settings` | A person in several organisations switches with a standard switcher; each organi… | system_default |
| D09 | `tenancy.role_visibility` | see build_model.D09 | derivation |
| T.04 | `tenancy.roles_scope` | null | question |
| T.08 | `tenancy.suspend_delete` | null | question |
| sys_org_switcher | `tenancy.switcher` | A person in several organisations switches with a standard switcher; each organi… | system_default |

## visual

| # | Field | Value | Source |
|---|---|---|---|
| sys_theme | `visual.accessibility` | Light theme only; WCAG 2.1 AA contrast and keyboard access. | system_default |
| C.04 | `visual.brand_assets` | {"mode": "design_for_me"} | question |
| C.03 | `visual.density` | balanced | question |
| C.01 | `visual.references` | none | question |
| sys_theme | `visual.theme` | Light theme only; WCAG 2.1 AA contrast and keyboard access. | system_default |
| C.02 | `visual.tone` | ["friendly", "simple", "warm"] | question |

## workflow

| # | Field | Value | Source |
|---|---|---|---|
| D08 | `workflow.*.transition_graph` | see build_model.D08 | derivation |
| FL.05:Appointment lifecycle | `workflow.Appointment lifecycle.approvals` | [] | question |
| FL.07:Appointment lifecycle | `workflow.Appointment lifecycle.cancel` | {"allowed": "no"} | question |
| FL.08:Appointment lifecycle | `workflow.Appointment lifecycle.on_complete` | Completed/No-show appointments lock and feed the reports. | question |
| FL.06:Appointment lifecycle | `workflow.Appointment lifecycle.on_reject` | null | question |
| FL.04:Appointment lifecycle | `workflow.Appointment lifecycle.preconditions` | [] | question |
| FL.09:Appointment lifecycle | `workflow.Appointment lifecycle.readonly_from` | Completed | question |
| FL.11:Appointment lifecycle | `workflow.Appointment lifecycle.stage_notifications` | [] | question |
| FL.02:Appointment lifecycle | `workflow.Appointment lifecycle.stages` | {"stages": ["Booked", "Confirmed", "Completed", "Cancelled", "No-show"], "initia… | question |
| FL.10:Appointment lifecycle | `workflow.Appointment lifecycle.timeouts` | [{"stage": "Booked", "duration": "24 hours", "then": "if the deposit is unpaid, … | question |
| FL.03:Appointment lifecycle | `workflow.Appointment lifecycle.transitions` | [{"from": "Booked", "to": "Confirmed", "mover": "roles", "roles": ["Staff"]}, {"… | question |
| FL.01:Appointment lifecycle | `workflow.Appointment lifecycle.trigger` | {"kind": "event", "event": "an appointment is created (public form or by staff);… | question |

## Build model summary

- Records: Service, Customer, Appointment
- Roles: Owner, Staff (super: Owner)
- Workflows: Appointment lifecycle
- Screens: 9 (`SPEC-BOOKING-FRONTDESK-REF` navigation order)
- Actions: 15
- Generated QA tests: 33
