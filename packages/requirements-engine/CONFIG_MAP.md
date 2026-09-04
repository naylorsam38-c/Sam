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


## crm-pipeline — CRM (modelled on Pipedrive)

Modules: people_directory, pipeline, activities. Roles: Admin, Sales manager, Sales rep (super: Admin). Records: Organisation, Contact, Deal, Activity. Still asked of every customer: 17 questions (identity, brand, imports, deviations, read-backs).

| Feature | Controlled by | Rule |
|---|---|---|
| Rep visibility (own vs all deals) | `R.05:Deal` | change 'Sales rep: own' to 'all' for a transparent-pipeline shop |
| Organisations layer | `A.15 records list` | remove 'Organisation' -> contacts stand alone; Deal loses its Organisation link |
| Lost reasons | `R.02:Deal` | edit the Lost reason option list |
| Pipeline stages | `FL.02:Deal pipeline` | rename/add stages; FL.03 transitions must be restated for any new stage |
| Win-rate reporting | `A.15 reports list` | remove 'Win rate' |


## booking-frontdesk — booking (modelled on Acuity Scheduling)

Modules: catalog_services, scheduling, people_directory, deposits. Roles: Owner, Staff (super: Owner). Records: Service, Customer, Appointment. Still asked of every customer: 18 questions (identity, brand, imports, deviations, read-backs, plus B.03).

| Feature | Controlled by | Rule |
|---|---|---|
| Deposits | `R.02:Service (Deposit required)` | set every Service's Deposit required = no -> A.09 flips to no, Part B drops, Booked auto-confirms |
| SMS reminders | `N.03 answers` | remove 'sms' from the channels -> DI.07 (SMS credentials) no longer needed |
| Customer accounts | `AU.01` | add 'public' self-registration and a 'Customer' role to let customers log in and see their own bookings (R.05:Appointment gains Customer: own) |
| Auto-cancel unpaid bookings | `FL.10:Appointment lifecycle` | change or delete the 24-hour Booked timeout |
| No-show tracking | `FL.02 stages` | remove the No-show stage and its report |


## erp-backbone — ERP (modelled on Odoo (sales + purchasing + inventory core))

Modules: catalog_products, people_directory, ordering, inventory. Roles: Admin, Operations, Sales, Purchasing, Warehouse (super: Admin). Records: Product, Supplier, Customer account, Purchase order, Purchase order line, Sales order, Sales order line, Stock adjustment. Still asked of every customer: 17 questions (identity, brand, imports, deviations, read-backs).

| Feature | Controlled by | Rule |
|---|---|---|
| Purchasing side | `A.15 records list` | remove Purchase order, Purchase order line, Supplier and the PO workflow -> sales-only inventory app |
| PO approval | `FL.05:Purchase order lifecycle` | empty the approvals list -> Draft->Confirmed needs no sign-off |
| Reorder alerts | `R.02:Product + A.15 notifications` | remove Reorder point field and the Low stock alert together |
| Role split | `A.15 roles + P.00` | small shops merge Sales/Purchasing/Warehouse into Operations; P.00 = yes lets one person hold several |
| Stock corrections audit | `R.08:Stock adjustment` | delete rights stay 'Operations only' to keep the adjustment trail honest — widen deliberately or not at all |


## accounting-ledger — accounting (modelled on Xero (invoicing core))

Modules: people_directory, invoicing, payments. Roles: Admin, Accountant, Advisor (super: Admin). Records: Contact, Invoice, Invoice line, Bill, Payment. Still asked of every customer: 17 questions (identity, brand, imports, deviations, read-backs).

| Feature | Controlled by | Rule |
|---|---|---|
| Invoice approval step | `FL.05:Invoice lifecycle` | empty the approvals list -> Draft goes straight to Awaiting payment (sole traders) |
| Bills side | `A.15 records list` | remove Bill and its lifecycle -> invoicing-only app; P&L expenses metric drops |
| Overdue chasing | `N.01:Payment reminder` | change the +3 days offset, or remove the notification to stop chasing |
| Accrual vs cash reporting | `RP.05:Profit and loss:revenue` | rewrite the definition to 'Payments received in the period' for cash basis — one answer, not a rebuild |
| Advisor access | `A.15 roles list` | remove Advisor -> external-accountant access disappears |


## Combining templates

Modules are the unit of combination, and 'combine' means: union the inventories, union the per-instance answers, re-run the checker. Shared record names (Contact, Customer account) must be reconciled to ONE record before the union — the checker fails on a record answered twice. Worked combinations that need no reconciliation beyond that: booking + accounting (Acuity's Customer becomes Xero's Contact with Type=customer); CRM + accounting (Pipedrive's Organisation becomes the Contact, Deals in Won feed invoice creation via an R.15 action); ERP + accounting (Sales order Closed triggers invoice creation — add one FL.11/notification or R.15 action, nothing structural).
