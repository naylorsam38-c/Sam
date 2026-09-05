# Connector

`SPEC-FRONTDOOR` — assembled from `crm-pipeline` against graph 3.0. Every field below is numbered by the question, default, or derivation that owns it — nothing here was guessed.

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
| AU.06 | `auth.invite_authority` | {"inviters": ["Admin", "Sales manager"], "default_role": "Sales rep"} | question |
| AU.06 | `auth.invite_default_role` | {"inviters": ["Admin", "Sales manager"], "default_role": "Sales rep"} | question |
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
| B.02 | `billing.charged_party` | null | question |
| B.04 | `billing.currency` | null | question |
| sys_billing_details | `billing.details_collection` | Card, billing address and tax IDs are collected by the gateway's hosted form; in… | system_default |
| sys_billing_details | `billing.invoices` | Card, billing address and tax IDs are collected by the gateway's hosted form; in… | system_default |
| B.01 | `billing.model` | null | question |
| B.08 | `billing.on_failure` | null | question |
| sys_limit_reached | `billing.on_limit_reached` | Hitting a plan limit shows an upgrade prompt, then blocks the action. | system_default |
| B.07 | `billing.payment_methods` | null | question |
| B.09 | `billing.plan_change` | null | question |
| D10 | `billing.plan_linkage` | see build_model.D10 | derivation |
| B.03 | `billing.plans` | null | question |
| sys_proration | `billing.proration_rule` | Mid-cycle plan changes are prorated by the gateway. | system_default |
| B.11 | `billing.refunds` | null | question |
| A.09 | `billing.required` | no | question |
| sys_tax_calculation | `billing.tax_calculation` | Tax computed by the payment gateway from the billing address. | system_default |
| B.05 | `billing.trial` | null | question |
| B.06 | `billing.usage_charge_timing` | null | question |
| B.06 | `billing.usage_unit` | null | question |
| sys_idempotency_webhook | `billing.webhook_handling` | Payment webhooks signature-verified and processed exactly once. | system_default |

## client

| # | Field | Value | Source |
|---|---|---|---|
| C.06 | `client.landing_screen_per_role` | {"Admin": "Pipeline board", "Sales manager": "Pipeline board", "Sales rep": "My … | question |
| C.05 | `client.mobile_behaviour` | {"mode": "simplified"} | question |
| C.07 | `client.navigation` | confirmed | question |
| D13 | `client.navigation.derived` | see build_model.D13 | derivation |
| A.06 | `client.platforms` | ["web"] | question |
| A.10 | `client.public_surfaces` | [] | question |

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

## integration

| # | Field | Value | Source |
|---|---|---|---|
| sys_retry_policy | `integration.*.retry_policy` | Failed external calls retry 3× with exponential backoff + jitter. | system_default |
| A.11 | `integration.public_api_required` | no | question |

## inventory

| # | Field | Value | Source |
|---|---|---|---|
| A.15 | `inventory.file_types` | [] | question |
| A.15 | `inventory.forms` | [] | question |
| A.15 | `inventory.integrations` | [] | question |
| A.15 | `inventory.notifications` | ["Activity due", "Deal won"] | question |
| A.15 | `inventory.records` | ["Organisation", "Contact", "Deal", "Activity"] | question |
| A.15 | `inventory.reports` | ["Pipeline by stage", "Win rate"] | question |
| A.15 | `inventory.roles` | ["Admin", "Sales manager", "Sales rep"] | question |
| A.15 | `inventory.screens` | [] | question |
| A.15 | `inventory.workflows` | ["Deal pipeline"] | question |

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
| N.03:Activity due | `notification.Activity due.channels` | ["email", "push", "in_app"] | question |
| N.04:Activity due | `notification.Activity due.intent` | This call/meeting/to-do is coming up — be ready or move it. | question |
| N.05:Activity due | `notification.Activity due.opt_out` | yes | question |
| N.02:Activity due | `notification.Activity due.recipients` | [{"kind": "field", "record": "Activity", "field": "Owner"}] | question |
| N.01:Activity due | `notification.Activity due.trigger` | {"kind": "relative_to_date", "record": "Activity", "date_field": "Due", "offset"… | question |
| N.03:Deal won | `notification.Deal won.channels` | ["in_app"] | question |
| N.04:Deal won | `notification.Deal won.intent` | A deal just closed — see who won it and its value. | question |
| N.05:Deal won | `notification.Deal won.opt_out` | yes | question |
| N.02:Deal won | `notification.Deal won.recipients` | [{"kind": "roles", "roles": ["Sales manager"]}] | question |
| N.01:Deal won | `notification.Deal won.trigger` | {"kind": "event", "event": "a deal moves to stage Won"} | question |

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
| A.03 | `product.audience` | The app's own roles are kept, so each person only sees and does their part. | question |
| A.01 | `product.description` | Something for connecting people — I want to keep everyone's details, see who is … | question |
| A.02 | `product.goals` | Use it to something for connecting people — i want to keep everyone's details, s… | question |
| A.05 | `product.name` | Connector | question |
| A.04 | `product.success_definition` | It is being used, and what it holds is what is really going on. | question |

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
| R.06:Activity | `record.Activity.access.create` | ["Sales rep", "Sales manager"] | question |
| R.08:Activity | `record.Activity.access.delete` | [{"role": "Sales rep", "scope": "own"}, {"role": "Sales manager", "scope": "all"… | question |
| R.07:Activity | `record.Activity.access.edit` | [{"role": "Sales rep", "scope": "own"}, {"role": "Sales manager", "scope": "all"… | question |
| R.05:Activity | `record.Activity.access.view` | [{"role": "Sales rep", "scope": "own"}, {"role": "Sales manager", "scope": "all"… | question |
| R.13:Activity | `record.Activity.archivable` | no | question |
| R.15:Activity | `record.Activity.custom_actions` | [] | question |
| R.02:Activity | `record.Activity.fields` | [{"name": "Subject", "type": "short_text", "required": "yes", "unique": "no"}, {… | question |
| R.10:Activity | `record.Activity.has_lifecycle` | {"has": "no"} | question |
| R.04:Activity | `record.Activity.human_id` | {"needed": "no"} | question |
| R.12:Activity | `record.Activity.on_delete` | delete_too | question |
| R.09:Activity | `record.Activity.ownership_rule` | {"basis": "field", "field": "Owner"} | question |
| R.01:Activity | `record.Activity.purpose` | A scheduled call, meeting or to-do attached to a deal. | question |
| R.11:Activity | `record.Activity.relations` | [{"target": "Deal", "cardinality": "one_to_many", "required": "yes"}] | question |
| R.14:Activity | `record.Activity.retention` | forever | question |
| R.03:Activity | `record.Activity.title_field` | Subject | question |
| R.06:Contact | `record.Contact.access.create` | ["Sales rep", "Sales manager"] | question |
| R.08:Contact | `record.Contact.access.delete` | [{"role": "Sales manager", "scope": "all"}] | question |
| R.07:Contact | `record.Contact.access.edit` | [{"role": "Sales rep", "scope": "all"}, {"role": "Sales manager", "scope": "all"… | question |
| R.05:Contact | `record.Contact.access.view` | [{"role": "Sales rep", "scope": "all"}, {"role": "Sales manager", "scope": "all"… | question |
| R.13:Contact | `record.Contact.archivable` | yes | question |
| R.15:Contact | `record.Contact.custom_actions` | [] | question |
| R.02:Contact | `record.Contact.fields` | [{"name": "Full name", "type": "short_text", "required": "yes", "unique": "no"},… | question |
| R.10:Contact | `record.Contact.has_lifecycle` | {"has": "no"} | question |
| R.04:Contact | `record.Contact.human_id` | {"needed": "no"} | question |
| R.12:Contact | `record.Contact.on_delete` | keep_unlinked | question |
| R.09:Contact | `record.Contact.ownership_rule` | null | question |
| R.01:Contact | `record.Contact.purpose` | A person at an organisation the business talks to. | question |
| R.11:Contact | `record.Contact.relations` | [{"target": "Organisation", "cardinality": "one_to_many", "required": "no"}] | question |
| R.14:Contact | `record.Contact.retention` | forever | question |
| R.03:Contact | `record.Contact.title_field` | Full name | question |
| R.06:Deal | `record.Deal.access.create` | ["Sales rep", "Sales manager"] | question |
| R.08:Deal | `record.Deal.access.delete` | [{"role": "Sales manager", "scope": "all"}] | question |
| R.07:Deal | `record.Deal.access.edit` | [{"role": "Sales rep", "scope": "own"}, {"role": "Sales manager", "scope": "all"… | question |
| R.05:Deal | `record.Deal.access.view` | [{"role": "Sales rep", "scope": "own"}, {"role": "Sales manager", "scope": "all"… | question |
| R.13:Deal | `record.Deal.archivable` | yes | question |
| R.15:Deal | `record.Deal.custom_actions` | [{"name": "Reassign", "who": ["Sales manager"], "effect": "changes the deal's Ow… | question |
| R.02:Deal | `record.Deal.fields` | [{"name": "Title", "type": "short_text", "required": "yes", "unique": "no"}, {"n… | question |
| R.10:Deal | `record.Deal.has_lifecycle` | {"has": "yes", "stages": ["Lead in", "Contacted", "Proposal sent", "Negotiation"… | question |
| R.04:Deal | `record.Deal.human_id` | {"needed": "no"} | question |
| R.12:Deal | `record.Deal.on_delete` | block | question |
| R.09:Deal | `record.Deal.ownership_rule` | {"basis": "field", "field": "Owner"} | question |
| R.01:Deal | `record.Deal.purpose` | A potential sale being worked through the pipeline. | question |
| R.11:Deal | `record.Deal.relations` | [{"target": "Contact", "cardinality": "one_to_many", "required": "yes"}, {"targe… | question |
| R.14:Deal | `record.Deal.retention` | forever | question |
| R.03:Deal | `record.Deal.title_field` | Title | question |
| R.06:Organisation | `record.Organisation.access.create` | ["Sales rep", "Sales manager"] | question |
| R.08:Organisation | `record.Organisation.access.delete` | [{"role": "Sales manager", "scope": "all"}] | question |
| R.07:Organisation | `record.Organisation.access.edit` | [{"role": "Sales rep", "scope": "all"}, {"role": "Sales manager", "scope": "all"… | question |
| R.05:Organisation | `record.Organisation.access.view` | [{"role": "Sales rep", "scope": "all"}, {"role": "Sales manager", "scope": "all"… | question |
| R.13:Organisation | `record.Organisation.archivable` | yes | question |
| R.15:Organisation | `record.Organisation.custom_actions` | [] | question |
| R.02:Organisation | `record.Organisation.fields` | [{"name": "Name", "type": "short_text", "required": "yes", "unique": "yes"}, {"n… | question |
| R.10:Organisation | `record.Organisation.has_lifecycle` | {"has": "no"} | question |
| R.04:Organisation | `record.Organisation.human_id` | {"needed": "no"} | question |
| R.12:Organisation | `record.Organisation.on_delete` | null | question |
| R.09:Organisation | `record.Organisation.ownership_rule` | null | question |
| R.01:Organisation | `record.Organisation.purpose` | A company the business sells to. | question |
| R.11:Organisation | `record.Organisation.relations` | [] | question |
| R.14:Organisation | `record.Organisation.retention` | forever | question |
| R.03:Organisation | `record.Organisation.title_field` | Name | question |

## report

| # | Field | Value | Source |
|---|---|---|---|
| sys_report_caching | `report.*.cache_policy` | Reports regenerate on demand, cached 5 min. | system_default |
| D07 | `report.*.data_source` | see build_model.D07 | derivation |
| D07 | `report.*.metric.*.derived_definition` | see build_model.D07 | derivation |
| RP.06:Pipeline by stage | `report.Pipeline by stage.default_range` | {"filters": ["Owner", "Expected close date"], "default_range": "all open deals"} | question |
| RP.07:Pipeline by stage | `report.Pipeline by stage.export` | {"allowed": "yes", "by": ["Sales manager"]} | question |
| RP.06:Pipeline by stage | `report.Pipeline by stage.filters` | {"filters": ["Owner", "Expected close date"], "default_range": "all open deals"} | question |
| RP.03:Pipeline by stage | `report.Pipeline by stage.form` | {"delivery": "screen", "shape": "both"} | question |
| RP.04:Pipeline by stage | `report.Pipeline by stage.metrics` | ["sum of open Deal Value grouped by stage", "count of Deals grouped by stage"] | question |
| RP.01:Pipeline by stage | `report.Pipeline by stage.question` | How much potential value sits in each stage of the pipeline? | question |
| RP.08:Pipeline by stage | `report.Pipeline by stage.scheduled_delivery` | {"enabled": "no"} | question |
| RP.02:Pipeline by stage | `report.Pipeline by stage.viewers` | ["Sales rep", "Sales manager"] | question |
| RP.06:Win rate | `report.Win rate.default_range` | {"filters": ["Owner"], "default_range": "last 90 days"} | question |
| RP.07:Win rate | `report.Win rate.export` | {"allowed": "yes", "by": ["Sales manager"]} | question |
| RP.06:Win rate | `report.Win rate.filters` | {"filters": ["Owner"], "default_range": "last 90 days"} | question |
| RP.03:Win rate | `report.Win rate.form` | {"delivery": "screen", "shape": "both"} | question |
| RP.05:Win rate:win rate | `report.Win rate.metric.win rate.definition` | deals that entered Won divided by deals that entered Won or Lost, in the selecte… | question |
| RP.04:Win rate | `report.Win rate.metrics` | ["win rate"] | question |
| RP.01:Win rate | `report.Win rate.question` | Of the deals we finish, what share do we win? | question |
| RP.08:Win rate | `report.Win rate.scheduled_delivery` | {"enabled": "no"} | question |
| RP.02:Win rate | `report.Win rate.viewers` | ["Sales manager"] | question |

## role

| # | Field | Value | Source |
|---|---|---|---|
| D04 | `role.*.forbidden_actions` | see build_model.D04 | derivation |
| D04 | `role.*.is_admin` | see build_model.D04 | derivation |
| D04 | `role.*.permitted_actions` | see build_model.D04 | derivation |
| D03 | `role.*.visible_screens` | see build_model.D03 | derivation |
| P.04:Admin | `role.Admin.assignable_by` | null | question |
| P.03:Admin | `role.Admin.billing_access` | null | question |
| P.01:Admin | `role.Admin.description` | null | question |
| P.02:Admin | `role.Admin.sees_private_data` | null | question |
| P.04:Sales manager | `role.Sales manager.assignable_by` | ["Admin"] | question |
| P.03:Sales manager | `role.Sales manager.billing_access` | null | question |
| P.01:Sales manager | `role.Sales manager.description` | Runs the sales team; sees and edits every deal. | question |
| P.02:Sales manager | `role.Sales manager.sees_private_data` | no | question |
| P.04:Sales rep | `role.Sales rep.assignable_by` | ["Admin", "Sales manager"] | question |
| P.03:Sales rep | `role.Sales rep.billing_access` | null | question |
| P.01:Sales rep | `role.Sales rep.description` | Works their own deals and activities. | question |
| P.02:Sales rep | `role.Sales rep.sees_private_data` | no | question |

## roles

| # | Field | Value | Source |
|---|---|---|---|
| P.00 | `roles.multi_role_per_person` | no | question |
| A.16 | `roles.super_role` | Admin | question |

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
| C.04 | `visual.brand_assets` | {"mode": "premade", "logo_id": "orbit"} | question |
| C.03 | `visual.density` | balanced | question |
| C.01 | `visual.references` | none | question |
| sys_theme | `visual.theme` | Light theme only; WCAG 2.1 AA contrast and keyboard access. | system_default |
| C.02 | `visual.tone` | ["visual", "open", "friendly"] | question |

## workflow

| # | Field | Value | Source |
|---|---|---|---|
| D08 | `workflow.*.transition_graph` | see build_model.D08 | derivation |
| FL.05:Deal pipeline | `workflow.Deal pipeline.approvals` | [] | question |
| FL.07:Deal pipeline | `workflow.Deal pipeline.cancel` | {"allowed": "no"} | question |
| FL.08:Deal pipeline | `workflow.Deal pipeline.on_complete` | Won: the deal locks and counts toward revenue reporting. Lost: Lost reason becom… | question |
| FL.06:Deal pipeline | `workflow.Deal pipeline.on_reject` | null | question |
| FL.04:Deal pipeline | `workflow.Deal pipeline.preconditions` | [] | question |
| FL.09:Deal pipeline | `workflow.Deal pipeline.readonly_from` | Won | question |
| FL.11:Deal pipeline | `workflow.Deal pipeline.stage_notifications` | [] | question |
| FL.02:Deal pipeline | `workflow.Deal pipeline.stages` | {"stages": ["Lead in", "Contacted", "Proposal sent", "Negotiation", "Won", "Lost… | question |
| FL.10:Deal pipeline | `workflow.Deal pipeline.timeouts` | [] | question |
| FL.03:Deal pipeline | `workflow.Deal pipeline.transitions` | [{"from": "Lead in", "to": "Contacted", "mover": "roles", "roles": ["Sales rep",… | question |
| FL.01:Deal pipeline | `workflow.Deal pipeline.trigger` | {"kind": "person", "who": ["Sales rep", "Sales manager"], "action": "creating a … | question |

## Build model summary

- Records: Organisation, Contact, Deal, Activity
- Roles: Admin, Sales manager, Sales rep (super: Admin)
- Workflows: Deal pipeline
- Screens: 10 (`SPEC-FRONTDOOR` navigation order)
- Actions: 21
- Generated QA tests: 68
