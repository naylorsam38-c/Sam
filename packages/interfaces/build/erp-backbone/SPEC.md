# Backbone (erp-backbone)

`SPEC-ERP-BACKBONE-REF` — assembled from `erp-backbone` against graph 3.0. Every field below is numbered by the question, default, or derivation that owns it — nothing here was guessed.

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
| AU.06 | `auth.invite_authority` | null | question |
| AU.06 | `auth.invite_default_role` | null | question |
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
| AU.01 | `auth.registration_modes` | ["admin_created"] | question |
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
| C.06 | `client.landing_screen_per_role` | {"Admin": "Stock on hand", "Operations": "Stock on hand", "Sales": "Sales orders… | question |
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
| A.15 | `inventory.notifications` | ["Low stock alert", "Order shipped"] | question |
| A.15 | `inventory.records` | ["Product", "Supplier", "Customer account", "Purchase order", "Purchase order li… | question |
| A.15 | `inventory.reports` | ["Stock on hand", "Sales by month", "Open orders"] | question |
| A.15 | `inventory.roles` | ["Admin", "Operations", "Sales", "Purchasing", "Warehouse"] | question |
| A.15 | `inventory.screens` | [] | question |
| A.15 | `inventory.workflows` | ["Purchase order lifecycle", "Sales order lifecycle"] | question |

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
| N.03:Low stock alert | `notification.Low stock alert.channels` | ["email", "in_app"] | question |
| N.04:Low stock alert | `notification.Low stock alert.intent` | This product is running out — raise a purchase order. | question |
| N.05:Low stock alert | `notification.Low stock alert.opt_out` | yes | question |
| N.02:Low stock alert | `notification.Low stock alert.recipients` | [{"kind": "roles", "roles": ["Purchasing", "Operations"]}] | question |
| N.01:Low stock alert | `notification.Low stock alert.trigger` | {"kind": "event", "event": "a Product's Stock on hand falls to or below its Reor… | question |
| N.03:Order shipped | `notification.Order shipped.channels` | ["in_app"] | question |
| N.04:Order shipped | `notification.Order shipped.intent` | The customer's order has left — tell them if they ask. | question |
| N.05:Order shipped | `notification.Order shipped.opt_out` | yes | question |
| N.02:Order shipped | `notification.Order shipped.recipients` | [{"kind": "roles", "roles": ["Sales"]}] | question |
| N.01:Order shipped | `notification.Order shipped.trigger` | {"kind": "event", "event": "a sales order moves to Shipped"} | question |

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
| A.03 | `product.audience` | A trading business: sales, purchasing, warehouse and operations staff. | question |
| A.01 | `product.description` | The operations core: products with stock on hand, suppliers and customer account… | question |
| A.02 | `product.goals` | Buy, sell and hold stock with every movement accounted for, and never run out un… | question |
| A.05 | `product.name` | Backbone | question |
| A.04 | `product.success_definition` | Stock on hand is always right and every open order is visible. | question |

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
| R.06:Customer account | `record.Customer account.access.create` | ["Sales", "Operations"] | question |
| R.08:Customer account | `record.Customer account.access.delete` | [{"role": "Operations", "scope": "all"}] | question |
| R.07:Customer account | `record.Customer account.access.edit` | [{"role": "Sales", "scope": "all"}, {"role": "Operations", "scope": "all"}] | question |
| R.05:Customer account | `record.Customer account.access.view` | [{"role": "Operations", "scope": "all"}, {"role": "Sales", "scope": "all"}, {"ro… | question |
| R.13:Customer account | `record.Customer account.archivable` | yes | question |
| R.15:Customer account | `record.Customer account.custom_actions` | [] | question |
| R.02:Customer account | `record.Customer account.fields` | [{"name": "Name", "type": "short_text", "required": "yes", "unique": "no"}, {"na… | question |
| R.10:Customer account | `record.Customer account.has_lifecycle` | {"has": "no"} | question |
| R.04:Customer account | `record.Customer account.human_id` | {"needed": "no"} | question |
| R.12:Customer account | `record.Customer account.on_delete` | null | question |
| R.09:Customer account | `record.Customer account.ownership_rule` | null | question |
| R.01:Customer account | `record.Customer account.purpose` | A company or person the business sells to. | question |
| R.11:Customer account | `record.Customer account.relations` | [] | question |
| R.14:Customer account | `record.Customer account.retention` | forever | question |
| R.03:Customer account | `record.Customer account.title_field` | Name | question |
| R.06:Product | `record.Product.access.create` | ["Operations"] | question |
| R.08:Product | `record.Product.access.delete` | [{"role": "Operations", "scope": "all"}] | question |
| R.07:Product | `record.Product.access.edit` | [{"role": "Operations", "scope": "all"}] | question |
| R.05:Product | `record.Product.access.view` | [{"role": "Operations", "scope": "all"}, {"role": "Sales", "scope": "all"}, {"ro… | question |
| R.13:Product | `record.Product.archivable` | yes | question |
| R.15:Product | `record.Product.custom_actions` | [] | question |
| R.02:Product | `record.Product.fields` | [{"name": "Name", "type": "short_text", "required": "yes", "unique": "no"}, {"na… | question |
| R.10:Product | `record.Product.has_lifecycle` | {"has": "no"} | question |
| R.04:Product | `record.Product.human_id` | {"needed": "no"} | question |
| R.12:Product | `record.Product.on_delete` | null | question |
| R.09:Product | `record.Product.ownership_rule` | null | question |
| R.01:Product | `record.Product.purpose` | An item the business buys, stocks and sells. | question |
| R.11:Product | `record.Product.relations` | [] | question |
| R.14:Product | `record.Product.retention` | forever | question |
| R.03:Product | `record.Product.title_field` | Name | question |
| R.06:Purchase order line | `record.Purchase order line.access.create` | ["Purchasing"] | question |
| R.08:Purchase order line | `record.Purchase order line.access.delete` | [{"role": "Purchasing", "scope": "all"}] | question |
| R.07:Purchase order line | `record.Purchase order line.access.edit` | [{"role": "Purchasing", "scope": "all"}] | question |
| R.05:Purchase order line | `record.Purchase order line.access.view` | [{"role": "Operations", "scope": "all"}, {"role": "Purchasing", "scope": "all"},… | question |
| R.13:Purchase order line | `record.Purchase order line.archivable` | no | question |
| R.15:Purchase order line | `record.Purchase order line.custom_actions` | [] | question |
| R.02:Purchase order line | `record.Purchase order line.fields` | [{"name": "Purchase order", "type": "link", "required": "yes", "unique": "no", "… | question |
| R.10:Purchase order line | `record.Purchase order line.has_lifecycle` | {"has": "no"} | question |
| R.04:Purchase order line | `record.Purchase order line.human_id` | {"needed": "no"} | question |
| R.12:Purchase order line | `record.Purchase order line.on_delete` | delete_too | question |
| R.09:Purchase order line | `record.Purchase order line.ownership_rule` | null | question |
| R.01:Purchase order line | `record.Purchase order line.purpose` | One product and quantity on a purchase order. | question |
| R.11:Purchase order line | `record.Purchase order line.relations` | [{"target": "Purchase order", "cardinality": "one_to_many", "required": "yes"}, … | question |
| R.14:Purchase order line | `record.Purchase order line.retention` | forever | question |
| R.03:Purchase order line | `record.Purchase order line.title_field` | Product | question |
| R.06:Purchase order | `record.Purchase order.access.create` | ["Purchasing"] | question |
| R.08:Purchase order | `record.Purchase order.access.delete` | [{"role": "Operations", "scope": "all"}] | question |
| R.07:Purchase order | `record.Purchase order.access.edit` | [{"role": "Purchasing", "scope": "all"}, {"role": "Operations", "scope": "all"}] | question |
| R.05:Purchase order | `record.Purchase order.access.view` | [{"role": "Operations", "scope": "all"}, {"role": "Purchasing", "scope": "all"},… | question |
| R.13:Purchase order | `record.Purchase order.archivable` | yes | question |
| R.15:Purchase order | `record.Purchase order.custom_actions` | [] | question |
| R.02:Purchase order | `record.Purchase order.fields` | [{"name": "Supplier", "type": "link", "required": "yes", "unique": "no", "target… | question |
| R.10:Purchase order | `record.Purchase order.has_lifecycle` | {"has": "yes", "stages": ["Draft", "Confirmed", "Received", "Closed", "Cancelled… | question |
| R.04:Purchase order | `record.Purchase order.human_id` | {"needed": "yes", "format": "PO-#### (sequential)"} | question |
| R.12:Purchase order | `record.Purchase order.on_delete` | block | question |
| R.09:Purchase order | `record.Purchase order.ownership_rule` | null | question |
| R.01:Purchase order | `record.Purchase order.purpose` | An order placed with a supplier to buy stock. | question |
| R.11:Purchase order | `record.Purchase order.relations` | [{"target": "Supplier", "cardinality": "one_to_many", "required": "yes"}] | question |
| R.14:Purchase order | `record.Purchase order.retention` | forever | question |
| R.03:Purchase order | `record.Purchase order.title_field` | Supplier | question |
| R.06:Sales order line | `record.Sales order line.access.create` | ["Sales"] | question |
| R.08:Sales order line | `record.Sales order line.access.delete` | [{"role": "Sales", "scope": "all"}] | question |
| R.07:Sales order line | `record.Sales order line.access.edit` | [{"role": "Sales", "scope": "all"}] | question |
| R.05:Sales order line | `record.Sales order line.access.view` | [{"role": "Operations", "scope": "all"}, {"role": "Sales", "scope": "all"}, {"ro… | question |
| R.13:Sales order line | `record.Sales order line.archivable` | no | question |
| R.15:Sales order line | `record.Sales order line.custom_actions` | [] | question |
| R.02:Sales order line | `record.Sales order line.fields` | [{"name": "Sales order", "type": "link", "required": "yes", "unique": "no", "tar… | question |
| R.10:Sales order line | `record.Sales order line.has_lifecycle` | {"has": "no"} | question |
| R.04:Sales order line | `record.Sales order line.human_id` | {"needed": "no"} | question |
| R.12:Sales order line | `record.Sales order line.on_delete` | delete_too | question |
| R.09:Sales order line | `record.Sales order line.ownership_rule` | null | question |
| R.01:Sales order line | `record.Sales order line.purpose` | One product and quantity on a sales order. | question |
| R.11:Sales order line | `record.Sales order line.relations` | [{"target": "Sales order", "cardinality": "one_to_many", "required": "yes"}, {"t… | question |
| R.14:Sales order line | `record.Sales order line.retention` | forever | question |
| R.03:Sales order line | `record.Sales order line.title_field` | Product | question |
| R.06:Sales order | `record.Sales order.access.create` | ["Sales"] | question |
| R.08:Sales order | `record.Sales order.access.delete` | [{"role": "Operations", "scope": "all"}] | question |
| R.07:Sales order | `record.Sales order.access.edit` | [{"role": "Sales", "scope": "all"}, {"role": "Operations", "scope": "all"}] | question |
| R.05:Sales order | `record.Sales order.access.view` | [{"role": "Operations", "scope": "all"}, {"role": "Sales", "scope": "all"}, {"ro… | question |
| R.13:Sales order | `record.Sales order.archivable` | yes | question |
| R.15:Sales order | `record.Sales order.custom_actions` | [] | question |
| R.02:Sales order | `record.Sales order.fields` | [{"name": "Customer account", "type": "link", "required": "yes", "unique": "no",… | question |
| R.10:Sales order | `record.Sales order.has_lifecycle` | {"has": "yes", "stages": ["Draft", "Confirmed", "Shipped", "Closed", "Cancelled"… | question |
| R.04:Sales order | `record.Sales order.human_id` | {"needed": "yes", "format": "SO-#### (sequential)"} | question |
| R.12:Sales order | `record.Sales order.on_delete` | block | question |
| R.09:Sales order | `record.Sales order.ownership_rule` | null | question |
| R.01:Sales order | `record.Sales order.purpose` | An order from a customer to be picked, shipped and invoiced. | question |
| R.11:Sales order | `record.Sales order.relations` | [{"target": "Customer account", "cardinality": "one_to_many", "required": "yes"}… | question |
| R.14:Sales order | `record.Sales order.retention` | forever | question |
| R.03:Sales order | `record.Sales order.title_field` | Customer account | question |
| R.06:Stock adjustment | `record.Stock adjustment.access.create` | ["Warehouse", "Operations"] | question |
| R.08:Stock adjustment | `record.Stock adjustment.access.delete` | [{"role": "Operations", "scope": "all"}] | question |
| R.07:Stock adjustment | `record.Stock adjustment.access.edit` | [{"role": "Operations", "scope": "all"}] | question |
| R.05:Stock adjustment | `record.Stock adjustment.access.view` | [{"role": "Operations", "scope": "all"}, {"role": "Warehouse", "scope": "all"}] | question |
| R.13:Stock adjustment | `record.Stock adjustment.archivable` | no | question |
| R.15:Stock adjustment | `record.Stock adjustment.custom_actions` | [] | question |
| R.02:Stock adjustment | `record.Stock adjustment.fields` | [{"name": "Product", "type": "link", "required": "yes", "unique": "no", "target_… | question |
| R.10:Stock adjustment | `record.Stock adjustment.has_lifecycle` | {"has": "no"} | question |
| R.04:Stock adjustment | `record.Stock adjustment.human_id` | {"needed": "no"} | question |
| R.12:Stock adjustment | `record.Stock adjustment.on_delete` | block | question |
| R.09:Stock adjustment | `record.Stock adjustment.ownership_rule` | null | question |
| R.01:Stock adjustment | `record.Stock adjustment.purpose` | A manual correction to a product's stock level, with a reason. | question |
| R.11:Stock adjustment | `record.Stock adjustment.relations` | [{"target": "Product", "cardinality": "one_to_many", "required": "yes"}] | question |
| R.14:Stock adjustment | `record.Stock adjustment.retention` | forever | question |
| R.03:Stock adjustment | `record.Stock adjustment.title_field` | Product | question |
| R.06:Supplier | `record.Supplier.access.create` | ["Purchasing", "Operations"] | question |
| R.08:Supplier | `record.Supplier.access.delete` | [{"role": "Operations", "scope": "all"}] | question |
| R.07:Supplier | `record.Supplier.access.edit` | [{"role": "Purchasing", "scope": "all"}, {"role": "Operations", "scope": "all"}] | question |
| R.05:Supplier | `record.Supplier.access.view` | [{"role": "Operations", "scope": "all"}, {"role": "Purchasing", "scope": "all"},… | question |
| R.13:Supplier | `record.Supplier.archivable` | yes | question |
| R.15:Supplier | `record.Supplier.custom_actions` | [] | question |
| R.02:Supplier | `record.Supplier.fields` | [{"name": "Name", "type": "short_text", "required": "yes", "unique": "yes"}, {"n… | question |
| R.10:Supplier | `record.Supplier.has_lifecycle` | {"has": "no"} | question |
| R.04:Supplier | `record.Supplier.human_id` | {"needed": "no"} | question |
| R.12:Supplier | `record.Supplier.on_delete` | null | question |
| R.09:Supplier | `record.Supplier.ownership_rule` | null | question |
| R.01:Supplier | `record.Supplier.purpose` | A company the business buys from. | question |
| R.11:Supplier | `record.Supplier.relations` | [] | question |
| R.14:Supplier | `record.Supplier.retention` | forever | question |
| R.03:Supplier | `record.Supplier.title_field` | Name | question |

## report

| # | Field | Value | Source |
|---|---|---|---|
| sys_report_caching | `report.*.cache_policy` | Reports regenerate on demand, cached 5 min. | system_default |
| D07 | `report.*.data_source` | see build_model.D07 | derivation |
| D07 | `report.*.metric.*.derived_definition` | see build_model.D07 | derivation |
| RP.06:Open orders | `report.Open orders.default_range` | {"filters": ["Supplier", "Customer account"], "default_range": "as at now"} | question |
| RP.07:Open orders | `report.Open orders.export` | {"allowed": "yes", "by": ["Operations"]} | question |
| RP.06:Open orders | `report.Open orders.filters` | {"filters": ["Supplier", "Customer account"], "default_range": "as at now"} | question |
| RP.03:Open orders | `report.Open orders.form` | {"delivery": "screen", "shape": "table"} | question |
| RP.04:Open orders | `report.Open orders.metrics` | ["count of Sales orders in Confirmed", "count of Purchase orders in Confirmed"] | question |
| RP.01:Open orders | `report.Open orders.question` | What is confirmed but not yet fulfilled, on both sides? | question |
| RP.08:Open orders | `report.Open orders.scheduled_delivery` | {"enabled": "no"} | question |
| RP.02:Open orders | `report.Open orders.viewers` | ["Operations", "Sales", "Purchasing", "Warehouse"] | question |
| RP.06:Sales by month | `report.Sales by month.default_range` | {"filters": ["Product", "Customer account"], "default_range": "last 12 months"} | question |
| RP.07:Sales by month | `report.Sales by month.export` | {"allowed": "yes", "by": ["Operations"]} | question |
| RP.06:Sales by month | `report.Sales by month.filters` | {"filters": ["Product", "Customer account"], "default_range": "last 12 months"} | question |
| RP.03:Sales by month | `report.Sales by month.form` | {"delivery": "both", "shape": "both"} | question |
| RP.04:Sales by month | `report.Sales by month.metrics` | ["sales value"] | question |
| RP.01:Sales by month | `report.Sales by month.question` | What did we sell, month by month? | question |
| RP.08:Sales by month | `report.Sales by month.scheduled_delivery` | {"enabled": "no"} | question |
| RP.02:Sales by month | `report.Sales by month.viewers` | ["Operations", "Sales"] | question |
| RP.06:Stock on hand | `report.Stock on hand.default_range` | {"filters": ["Product"], "default_range": "as at now"} | question |
| RP.07:Stock on hand | `report.Stock on hand.export` | {"allowed": "yes", "by": ["Operations"]} | question |
| RP.06:Stock on hand | `report.Stock on hand.filters` | {"filters": ["Product"], "default_range": "as at now"} | question |
| RP.03:Stock on hand | `report.Stock on hand.form` | {"delivery": "screen", "shape": "table"} | question |
| RP.04:Stock on hand | `report.Stock on hand.metrics` | ["sum of Product Stock on hand", "count of Products at or below Reorder point"] | question |
| RP.01:Stock on hand | `report.Stock on hand.question` | What do we hold right now, and what is at or below its reorder point? | question |
| RP.08:Stock on hand | `report.Stock on hand.scheduled_delivery` | {"enabled": "no"} | question |
| RP.02:Stock on hand | `report.Stock on hand.viewers` | ["Operations", "Sales", "Purchasing", "Warehouse"] | question |

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
| P.04:Operations | `role.Operations.assignable_by` | ["Admin"] | question |
| P.03:Operations | `role.Operations.billing_access` | null | question |
| P.01:Operations | `role.Operations.description` | Oversees the whole flow; approves purchases and closes orders. | question |
| P.02:Operations | `role.Operations.sees_private_data` | no | question |
| P.04:Purchasing | `role.Purchasing.assignable_by` | ["Admin"] | question |
| P.03:Purchasing | `role.Purchasing.billing_access` | null | question |
| P.01:Purchasing | `role.Purchasing.description` | Buys stock and manages suppliers. | question |
| P.02:Purchasing | `role.Purchasing.sees_private_data` | no | question |
| P.04:Sales | `role.Sales.assignable_by` | ["Admin"] | question |
| P.03:Sales | `role.Sales.billing_access` | null | question |
| P.01:Sales | `role.Sales.description` | Takes customer orders and manages customer accounts. | question |
| P.02:Sales | `role.Sales.sees_private_data` | no | question |
| P.04:Warehouse | `role.Warehouse.assignable_by` | ["Admin"] | question |
| P.03:Warehouse | `role.Warehouse.billing_access` | null | question |
| P.01:Warehouse | `role.Warehouse.description` | Receives, ships and corrects stock. | question |
| P.02:Warehouse | `role.Warehouse.sees_private_data` | no | question |

## roles

| # | Field | Value | Source |
|---|---|---|---|
| P.00 | `roles.multi_role_per_person` | yes | question |
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
| C.04 | `visual.brand_assets` | {"mode": "design_for_me"} | question |
| C.03 | `visual.density` | balanced | question |
| C.01 | `visual.references` | none | question |
| sys_theme | `visual.theme` | Light theme only; WCAG 2.1 AA contrast and keyboard access. | system_default |
| C.02 | `visual.tone` | ["dense", "precise", "serious"] | question |

## workflow

| # | Field | Value | Source |
|---|---|---|---|
| D08 | `workflow.*.transition_graph` | see build_model.D08 | derivation |
| FL.05:Purchase order lifecycle | `workflow.Purchase order lifecycle.approvals` | [{"stage": "Draft", "approvers": ["Operations"]}] | question |
| FL.07:Purchase order lifecycle | `workflow.Purchase order lifecycle.cancel` | {"allowed": "no"} | question |
| FL.08:Purchase order lifecycle | `workflow.Purchase order lifecycle.on_complete` | On Received, each line's Quantity is added to its Product's Stock on hand. | question |
| FL.06:Purchase order lifecycle | `workflow.Purchase order lifecycle.on_reject` | {"back_to": "Draft", "resubmit": "yes"} | question |
| FL.04:Purchase order lifecycle | `workflow.Purchase order lifecycle.preconditions` | [] | question |
| FL.09:Purchase order lifecycle | `workflow.Purchase order lifecycle.readonly_from` | Received | question |
| FL.11:Purchase order lifecycle | `workflow.Purchase order lifecycle.stage_notifications` | [] | question |
| FL.02:Purchase order lifecycle | `workflow.Purchase order lifecycle.stages` | {"stages": ["Draft", "Confirmed", "Received", "Closed", "Cancelled"], "initial":… | question |
| FL.10:Purchase order lifecycle | `workflow.Purchase order lifecycle.timeouts` | [] | question |
| FL.03:Purchase order lifecycle | `workflow.Purchase order lifecycle.transitions` | [{"from": "Draft", "to": "Confirmed", "mover": "roles", "roles": ["Purchasing"]}… | question |
| FL.01:Purchase order lifecycle | `workflow.Purchase order lifecycle.trigger` | {"kind": "person", "who": ["Purchasing"], "action": "creating a purchase order (… | question |
| FL.05:Sales order lifecycle | `workflow.Sales order lifecycle.approvals` | [] | question |
| FL.07:Sales order lifecycle | `workflow.Sales order lifecycle.cancel` | {"allowed": "no"} | question |
| FL.08:Sales order lifecycle | `workflow.Sales order lifecycle.on_complete` | On Shipped, each line's Quantity is subtracted from its Product's Stock on hand. | question |
| FL.06:Sales order lifecycle | `workflow.Sales order lifecycle.on_reject` | null | question |
| FL.04:Sales order lifecycle | `workflow.Sales order lifecycle.preconditions` | [] | question |
| FL.09:Sales order lifecycle | `workflow.Sales order lifecycle.readonly_from` | Shipped | question |
| FL.11:Sales order lifecycle | `workflow.Sales order lifecycle.stage_notifications` | [] | question |
| FL.02:Sales order lifecycle | `workflow.Sales order lifecycle.stages` | {"stages": ["Draft", "Confirmed", "Shipped", "Closed", "Cancelled"], "initial": … | question |
| FL.10:Sales order lifecycle | `workflow.Sales order lifecycle.timeouts` | [] | question |
| FL.03:Sales order lifecycle | `workflow.Sales order lifecycle.transitions` | [{"from": "Draft", "to": "Confirmed", "mover": "roles", "roles": ["Sales"]}, {"f… | question |
| FL.01:Sales order lifecycle | `workflow.Sales order lifecycle.trigger` | {"kind": "person", "who": ["Sales"], "action": "creating a sales order (starts i… | question |

## Build model summary

- Records: Product, Supplier, Customer account, Purchase order, Purchase order line, Sales order, Sales order line, Stock adjustment
- Roles: Admin, Operations, Sales, Purchasing, Warehouse (super: Admin)
- Workflows: Purchase order lifecycle, Sales order lifecycle
- Screens: 19 (`SPEC-ERP-BACKBONE-REF` navigation order)
- Actions: 31
- Generated QA tests: 133
