# Config map — interview answers -> template features

A template is a saved answer set for `question_graph_v3.json`. The builder assembles modules and applies these answers; the customer changes a feature by changing the named interview answer, never by redesigning. Removing an item from the A.15 inventory removes every per-instance answer keyed to it (the checker proves nothing is left dangling).


## pm-teamwork — project management (modelled on Asana)

Modules: tasking, collaboration, files. Roles: Admin, Member, Guest (super: Admin). Records: Project, Task, Comment. Still asked of every customer: 17 questions (identity, brand, imports, deviations, read-backs).

| Feature | Controlled by | Rule |
|---|---|---|
| Guest access | `A.15 roles list` | remove role 'Guest' -> every Guest grant and the invite path for guests disappears |
| Attachments | `A.15 file_types list` | remove 'Attachment' -> files module drops out entirely |
| Priorities | `R.02:Task` | delete the Priority field -> filter and report grouping on it drop out |
| Task duplication | `R.15:Task` | delete the Duplicate action |
| Due-date reminders | `A.15 notifications list` | remove 'Task due reminder' |

**Specialist engines this app runs** (7) — read straight off this template's own real data, not a separate exercise:

*Workflow/lifecycle engines:*
- `Task lifecycle` — stages ['To do', 'In progress', 'Done']; moved by ['Member']

*Notification/reminder engines:*
- `Task assigned` — trigger: event; channels: ['email', 'in_app']
- `Task due reminder` — trigger: relative_to_date; channels: ['email', 'in_app']
- `New comment` — trigger: event; channels: ['in_app']

*Reporting engines:*
- `Open tasks by person` — screen/both; metrics: ['count of Tasks not in stage Done, grouped by Assignee']
- `Overdue tasks` — screen/table; metrics: ['count of overdue Tasks']

*Custom record-action engines:*
- `Duplicate` on Task — creates a copy of the task in stage 'To do' with '(copy)' appended to the title


## crm-pipeline — CRM (modelled on Pipedrive)

Modules: people_directory, pipeline, activities. Roles: Admin, Sales manager, Sales rep (super: Admin). Records: Organisation, Contact, Deal, Activity. Still asked of every customer: 17 questions (identity, brand, imports, deviations, read-backs).

| Feature | Controlled by | Rule |
|---|---|---|
| Rep visibility (own vs all deals) | `R.05:Deal` | change 'Sales rep: own' to 'all' for a transparent-pipeline shop |
| Organisations layer | `A.15 records list` | remove 'Organisation' -> contacts stand alone; Deal loses its Organisation link |
| Lost reasons | `R.02:Deal` | edit the Lost reason option list |
| Pipeline stages | `FL.02:Deal pipeline` | rename/add stages; FL.03 transitions must be restated for any new stage |
| Win-rate reporting | `A.15 reports list` | remove 'Win rate' |

**Specialist engines this app runs** (6) — read straight off this template's own real data, not a separate exercise:

*Workflow/lifecycle engines:*
- `Deal pipeline` — stages ['Lead in', 'Contacted', 'Proposal sent', 'Negotiation', 'Won', 'Lost']; moved by ['Sales manager', 'Sales rep']

*Notification/reminder engines:*
- `Activity due` — trigger: relative_to_date; channels: ['email', 'push', 'in_app']
- `Deal won` — trigger: event; channels: ['in_app']

*Reporting engines:*
- `Pipeline by stage` — screen/both; metrics: ['sum of open Deal Value grouped by stage', 'count of Deals grouped by stage']
- `Win rate` — screen/both; metrics: ['win rate']

*Custom record-action engines:*
- `Reassign` on Deal — changes the deal's Owner to another person


## booking-frontdesk — booking (modelled on Acuity Scheduling)

Modules: catalog_services, scheduling, people_directory, deposits. Roles: Owner, Staff (super: Owner). Records: Service, Customer, Appointment. Still asked of every customer: 18 questions (identity, brand, imports, deviations, read-backs, plus B.03).

| Feature | Controlled by | Rule |
|---|---|---|
| Deposits | `R.02:Service (Deposit required)` | set every Service's Deposit required = no -> A.09 flips to no, Part B drops, Booked auto-confirms |
| SMS reminders | `N.03 answers` | remove 'sms' from the channels -> DI.07 (SMS credentials) no longer needed |
| Customer accounts | `AU.01` | add 'public' self-registration and a 'Customer' role to let customers log in and see their own bookings (R.05:Appointment gains Customer: own) |
| Auto-cancel unpaid bookings | `FL.10:Appointment lifecycle` | change or delete the 24-hour Booked timeout |
| No-show tracking | `FL.02 stages` | remove the No-show stage and its report |

**Specialist engines this app runs** (6) — read straight off this template's own real data, not a separate exercise:

*Workflow/lifecycle engines:*
- `Appointment lifecycle` — stages ['Booked', 'Confirmed', 'Completed', 'Cancelled', 'No-show']; moved by ['Staff']; has timeouts

*Notification/reminder engines:*
- `Booking confirmation` — trigger: event; channels: ['email', 'sms']
- `Appointment reminder` — trigger: relative_to_date; channels: ['email', 'sms']
- `Cancellation notice` — trigger: event; channels: ['email']

*Reporting engines:*
- `Upcoming appointments` — screen/table; metrics: ['count of Appointments in stage Booked or Confirmed']
- `No-show rate` — screen/both; metrics: ['no-show rate']


## erp-backbone — ERP (modelled on Odoo (sales + purchasing + inventory core))

Modules: catalog_products, people_directory, ordering, inventory. Roles: Admin, Operations, Sales, Purchasing, Warehouse (super: Admin). Records: Product, Supplier, Customer account, Purchase order, Purchase order line, Sales order, Sales order line, Stock adjustment. Still asked of every customer: 17 questions (identity, brand, imports, deviations, read-backs).

| Feature | Controlled by | Rule |
|---|---|---|
| Purchasing side | `A.15 records list` | remove Purchase order, Purchase order line, Supplier and the PO workflow -> sales-only inventory app |
| PO approval | `FL.05:Purchase order lifecycle` | empty the approvals list -> Draft->Confirmed needs no sign-off |
| Reorder alerts | `R.02:Product + A.15 notifications` | remove Reorder point field and the Low stock alert together |
| Role split | `A.15 roles + P.00` | small shops merge Sales/Purchasing/Warehouse into Operations; P.00 = yes lets one person hold several |
| Stock corrections audit | `R.08:Stock adjustment` | delete rights stay 'Operations only' to keep the adjustment trail honest — widen deliberately or not at all |

**Specialist engines this app runs** (7) — read straight off this template's own real data, not a separate exercise:

*Workflow/lifecycle engines:*
- `Purchase order lifecycle` — stages ['Draft', 'Confirmed', 'Received', 'Closed', 'Cancelled']; moved by ['Operations', 'Purchasing', 'Warehouse']; has approvals
- `Sales order lifecycle` — stages ['Draft', 'Confirmed', 'Shipped', 'Closed', 'Cancelled']; moved by ['Operations', 'Sales', 'Warehouse']

*Notification/reminder engines:*
- `Low stock alert` — trigger: event; channels: ['email', 'in_app']
- `Order shipped` — trigger: event; channels: ['in_app']

*Reporting engines:*
- `Stock on hand` — screen/table; metrics: ['sum of Product Stock on hand', 'count of Products at or below Reorder point']
- `Sales by month` — both/both; metrics: ['sales value']
- `Open orders` — screen/table; metrics: ['count of Sales orders in Confirmed', 'count of Purchase orders in Confirmed']


## accounting-ledger — accounting (modelled on Xero (invoicing core))

Modules: people_directory, invoicing, payments. Roles: Admin, Accountant, Advisor (super: Admin). Records: Contact, Invoice, Invoice line, Bill, Payment. Still asked of every customer: 17 questions (identity, brand, imports, deviations, read-backs).

| Feature | Controlled by | Rule |
|---|---|---|
| Invoice approval step | `FL.05:Invoice lifecycle` | empty the approvals list -> Draft goes straight to Awaiting payment (sole traders) |
| Bills side | `A.15 records list` | remove Bill and its lifecycle -> invoicing-only app |
| Overdue chasing | `N.01:Payment reminder` | change the +3 days offset, or remove the notification to stop chasing |
| Advisor access | `A.15 roles list` | remove Advisor -> external-accountant access disappears |

**Specialist engines this app runs** (6) — read straight off this template's own real data, not a separate exercise:

*Workflow/lifecycle engines:*
- `Invoice lifecycle` — stages ['Draft', 'Awaiting approval', 'Awaiting payment', 'Paid', 'Voided']; moved by ['Accountant', 'Admin']; automatic on: ['Payments applied to the invoice reach its total']; has approvals
- `Bill lifecycle` — stages ['Draft', 'Awaiting payment', 'Paid', 'Voided']; moved by ['Accountant', 'Admin']; automatic on: ['Payments applied to the bill reach its total']

*Notification/reminder engines:*
- `Invoice sent` — trigger: event; channels: ['email']
- `Payment reminder` — trigger: relative_to_date; channels: ['email']
- `Payment received` — trigger: event; channels: ['in_app']

*Custom record-action engines:*
- `Send` on Invoice — emails the invoice document to the Contact and stamps the sent time


## Combining templates

Modules are the unit of combination, and 'combine' means: union the inventories, union the per-instance answers, re-run the checker. Shared record names (Contact, Customer account) must be reconciled to ONE record before the union — the checker fails on a record answered twice. Worked combinations that need no reconciliation beyond that: booking + accounting (Acuity's Customer becomes Xero's Contact with Type=customer); CRM + accounting (Pipedrive's Organisation becomes the Contact, Deals in Won feed invoice creation via an R.15 action); ERP + accounting (Sales order Closed triggers invoice creation — add one FL.11/notification or R.15 action, nothing structural).
