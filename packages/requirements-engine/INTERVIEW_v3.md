# Requirements Interview v3.0

Generated from `question_graph_v3.json` by `build_graph.py`. Do not edit by hand — edit the graph and rebuild.

Every question has an ID, an answer type, a gate (when it is asked), a done-rule (what counts as answered — the script decides, not the model), and the spec fields it fills. Per-instance parts repeat once per confirmed item from A.15. The super role from A.16 is skipped in every authority question.

**61 fixed questions, 61 per-instance template questions, 47 locked defaults, 15 derivations, 11 deploy inputs, 222 spec fields each with exactly one source.**


## Part 0 — Setup

Asked once. Changes how much the interviewer asks, never what gets built or verified.

**0.01** — How involved do you want to be? Full (you decide everything), guided (you decide the product things, I'll propose the rest and you confirm), or hands-off (you answer the essentials, I'll fill the rest with standard behaviour and show you the list at the end).  
<br>type: `choice` · options: `full`, `guided`, `hands-off` · done when: `{"rule": "one_of", "options": ["full", "guided", "hands-off"]}` · fills: `engine.involvement`
<br>*Why: Sets how many derived/defaulted values are read back for confirmation. Never changes the spec's content.*


## Part A — The idea

Conversational. The interviewer may ask these in any words; the script decides when each field is filled.

**A.01** — What are you trying to build? Describe it like you're explaining it to a friend.  
<br>type: `text` · done when: `{"rule": "non_empty_and_extracts", "must_extract": ["records"]}` · fills: `product.description`
<br>*Why: Done only when at least one record noun can be extracted. Feeds the A.15 inventory proposal.*

**A.02** — What should people be able to accomplish with it?  
<br>type: `text` · done when: `{"rule": "non_empty"}` · fills: `product.goals`

**A.03** — Who is it for?  
<br>type: `text` · done when: `{"rule": "non_empty"}` · fills: `product.audience`

**A.04** — How will you know it's working — what does success look like to you?  
<br>type: `text` · done when: `{"rule": "non_empty"}` · fills: `product.success_definition`

**A.05** — What is the app called?  
<br>type: `text` · done when: `{"rule": "non_empty"}` · fills: `product.name`
<br>*Why: Dropped in the handoff's final pass. It appears on every screen and email; two builders would invent two names.*

**A.06** — Where will people use it — in a web browser, as a phone app (iOS/Android), both, or as a desktop program?  
<br>type: `multi` · options: `web`, `ios`, `android`, `desktop` · visual: `icon_multi` · done when: `{"rule": "subset_min1", "options": ["web", "ios", "android", "desktop"]}` · fills: `client.platforms`
<br>*Why: Never asked in the handoff. The single biggest divergence between two builders.*

**A.07** — Do people need to log in / have accounts?  
<br>type: `yesno` · options: `yes`, `no` · done when: `{"rule": "one_of", "options": ["yes", "no"]}` · fills: `auth.required`

**A.08** — Is this for one organisation/user base, or for many separate organisations that must never see each other's data?  
<br>type: `choice` · options: `single`, `multiple` · done when: `{"rule": "one_of", "options": ["single", "multiple"]}` · fills: `tenancy.mode`

**A.09** — Does this involve charging people money?  
<br>type: `yesno` · options: `yes`, `no` · done when: `{"rule": "one_of", "options": ["yes", "no"]}` · fills: `billing.required`

**A.10** — Which parts, if any, can be seen without logging in? (e.g. a public landing page, a public booking form, nothing)  
<br>type: `list` · asked if: A.07 = yes · visual: `screen_map` · done when: `{"rule": "min_items", "n": 0}` · fills: `client.public_surfaces`
<br>*Why: 'Nothing' is a valid answer and must be recorded explicitly.*

**A.11** — Do other systems need to push data into, or pull data out of, your app automatically (an API, webhooks)?  
<br>type: `yesno` · options: `yes`, `no` · done when: `{"rule": "one_of", "options": ["yes", "no"]}` · fills: `integration.public_api_required` · creates: `{"kind": "integration", "name": "Public API", "when": "yes"}`

**A.12** — Is there existing data that has to be brought in before launch (a spreadsheet, an old system)? If so, what and where from?  
<br>type: `structured` · done when: `{"rule": "structured", "keys": ["required"], "if": {"required": "yes", "then_keys": ["sources"]}}` · fills: `data.import_required`, `data.import_sources`

**A.13** — What country are most of your users in, and do you need more than one language?  
<br>type: `structured` · done when: `{"rule": "structured", "keys": ["region", "languages"]}` · fills: `locale.primary_region`, `locale.languages`
<br>*Why: Drives date/number/currency display format and default timezone. Never asked in the handoff.*

**A.14** — Is there anything you want to work differently from how a typical app of this kind normally works?  
<br>type: `list` · done when: `{"rule": "min_items", "n": 0}` · fills: `deviation.flags` · creates: `{"kind": "deviation", "each": true}`

**A.15** — Here's what I understood you'll need — screens, records, roles, forms, notifications, file types, reports, workflows, external systems. Did I miss anything, or get anything wrong? (confirm each list)  
<br>type: `confirm` · visual: `card_board` · done when: `{"rule": "confirmed_lists", "lists": ["screens", "records", "roles", "forms", "notifications", "file_types", "reports", "workflows", "integrations"]}` · fills: `inventory.screens`, `inventory.records`, `inventory.roles`, `inventory.forms`, `inventory.notifications`, `inventory.file_types`, `inventory.reports`, `inventory.workflows`, `inventory.integrations`
<br>*Why: Engine proposes from A.01–A.04; owner corrects. Each confirmed item instantiates its part. Empty lists are allowed but must be confirmed empty.*

**A.16** — Is there one role that can always do everything, no matter what? If so, which one?  
<br>type: `choice` · options: `<a confirmed role>`, `none` · asked if: A.07 = yes · done when: `{"rule": "role_or_none"}` · fills: `roles.super_role`
<br>*Why: That role is skipped in every per-record/per-workflow authority question and granted everything. Removes dozens of repeat answers.*


## Part C — Client — look, feel and navigation

**C.01** — Are there other apps, brands or products whose look and feel you want this to resemble — or specifically avoid?  
<br>type: `text` · visual: `style_board` · done when: `{"rule": "non_empty_or_none"}` · fills: `visual.references`

**C.02** — In three words, how should this feel to use? (e.g. playful, fast, minimal / serious, trustworthy, dense)  
<br>type: `list` · visual: `chip_select` · done when: `{"rule": "min_items", "n": 3}` · fills: `visual.tone`

**C.03** — How much should be visible at once — spacious and simple, balanced, or dense and information-rich?  
<br>type: `choice` · options: `spacious`, `balanced`, `dense` · visual: `visual_abc` · done when: `{"rule": "one_of", "options": ["spacious", "balanced", "dense"]}` · fills: `visual.density`

**C.04** — Is there a primary colour, logo or existing brand material to build from, or should that be designed for you?  
<br>type: `structured` · visual: `brand_kit` · done when: `{"rule": "structured", "keys": ["mode"], "one_of": {"mode": ["provided", "design_for_me"]}}` · fills: `visual.brand_assets`

**C.05** — On phones, should it be a simplified version of the big-screen layout, or does anything need to work completely differently on mobile?  
<br>type: `structured` · asked if: A.06 includes any of ['web', 'desktop'] · visual: `visual_abc` · done when: `{"rule": "structured", "keys": ["mode"], "one_of": {"mode": ["simplified", "different"]}, "if": {"mode": "different", "then_keys": ["what"]}}` · fills: `client.mobile_behaviour`
<br>*Why: Only asked if there is a big-screen platform to simplify from.*

**C.06** — After logging in, which screen does each role land on first?  
<br>type: `structured` · asked if: A.07 = yes · visual: `screen_picker` · done when: `{"rule": "map_complete", "keys_from": "inventory.roles", "values_from": "inventory.screens"}` · fills: `client.landing_screen_per_role`
<br>*Why: Handoff classed 'what happens after login' as a system default. It is product-specific: dashboard vs list vs record. Two builders diverge.*

**C.07** — Here is the main menu I'd build from your screens, in this order: [derived]. Reorder, rename or hide anything?  
<br>type: `confirm` · visual: `drag_order` · done when: `{"rule": "confirmed"}` · fills: `client.navigation`


## Part AU — Auth

*(asked only if A.07 = yes)*

**AU.01** — How do people get an account — sign up themselves publicly, get invited by someone, or get created by an admin? (any that apply)  
<br>type: `multi` · options: `public`, `invited`, `admin_created` · visual: `icon_multi` · done when: `{"rule": "subset_min1", "options": ["public", "invited", "admin_created"]}` · fills: `auth.registration_modes`

**AU.02** — What information do you need from someone when they register? (each item: what it is, and is it required)  
<br>type: `structured` · visual: `form_builder` · done when: `{"rule": "fields_list", "min": 1, "type_options": "FIELD_TYPES"}` · fills: `auth.registration_fields`

**AU.03** — Must they verify their email address before they can use the app?  
<br>type: `yesno` · options: `yes`, `no` · done when: `{"rule": "one_of", "options": ["yes", "no"]}` · fills: `auth.email_verification`

**AU.04** — Which login methods? (any that apply)  
<br>type: `multi` · options: `password`, `google`, `microsoft`, `apple`, `magic_link` · visual: `login_preview` · done when: `{"rule": "subset_min1", "options": ["password", "google", "microsoft", "apple", "magic_link"]}` · fills: `auth.methods`

**AU.05** — When someone signs up by themselves, which role do they get?  
<br>type: `choice` · options: `<a confirmed role>` · asked if: AU.01 includes public · done when: `{"rule": "role"}` · fills: `auth.default_role`
<br>*Why: Never asked in the handoff. Without it one builder makes new signups Members, another makes them Admins.*

**AU.06** — Who can invite people, and which role does an invited person get by default?  
<br>type: `structured` · asked if: AU.01 includes invited · done when: `{"rule": "structured", "keys": ["inviters", "default_role"], "roles_keys": ["inviters", "default_role"]}` · fills: `auth.invite_authority`, `auth.invite_default_role`

**AU.07** — Is two-factor authentication required — for nobody, admins only, or everyone? And by which method — authenticator app, SMS code, or either?  
<br>type: `structured` · done when: `{"rule": "structured", "keys": ["scope", "method"], "one_of": {"scope": ["nobody", "admins", "everyone"], "method": ["app", "sms", "either", "n/a"]}, "if": {"scope": "nobody", "then_value": {"method": "n/a"}}}` · fills: `auth.mfa_scope`, `auth.mfa_method`
<br>*Why: Handoff's classification said MFA method stays a closed question; the final interview lost it.*

**AU.08** — After how many failed login attempts should an account be temporarily locked, and for how long? ('never lock' is a valid answer)  
<br>type: `structured` · done when: `{"rule": "structured", "keys": ["attempts", "duration"], "or_value": "never"}` · fills: `auth.lockout_attempts`, `auth.lockout_duration`

**AU.09** — Can one person be logged in on more than one device at the same time?  
<br>type: `yesno` · options: `yes`, `no` · done when: `{"rule": "one_of", "options": ["yes", "no"]}` · fills: `auth.multi_device`

**AU.10** — How long can someone stay signed in before being asked to sign in again?  
<br>type: `duration` · done when: `{"rule": "duration_or_never"}` · fills: `auth.session_length`

**AU.11** — Can accounts be suspended? If so, who can do it, and does anything trigger it automatically (e.g. unpaid bill)?  
<br>type: `structured` · done when: `{"rule": "structured", "keys": ["allowed"], "if": {"allowed": "yes", "then_keys": ["by", "auto_triggers"]}, "roles_keys": ["by"]}` · fills: `auth.suspension_allowed`, `auth.suspension_by`, `auth.suspension_auto_triggers`

**AU.12** — Can accounts be deleted? By whom — the person themselves, an admin, or both? And what happens to their data: kept, anonymised, or fully erased?  
<br>type: `structured` · done when: `{"rule": "structured", "keys": ["allowed"], "if": {"allowed": "yes", "then_keys": ["by", "data"]}, "one_of": {"by": ["self", "admin", "both"], "data": ["kept", "anonymised", "erased"]}}` · fills: `auth.deletion_allowed`, `auth.deletion_by`, `auth.deletion_data_policy`

**AU.13** — Who, if anyone, may reset someone else's password on their behalf?  
<br>type: `roles` · done when: `{"rule": "roles_or_nobody"}` · fills: `auth.reset_others_by`

**AU.14** — Must people accept terms of service / a privacy policy when they sign up? Do those documents exist already?  
<br>type: `structured` · done when: `{"rule": "structured", "keys": ["required"], "if": {"required": "yes", "then_keys": ["status"]}, "one_of": {"status": ["have_them", "need_drafting"]}}` · fills: `legal.terms_required`, `legal.terms_status`


## Part P — Permissions — roles

*(asked only if A.07 = yes; repeats once per confirmed **role**)*

Once per confirmed role, except the super role from A.16. Authority over specific things is asked where it is exercised (Records, Flow, Billing).

**P.00** — Can one person hold more than one role at the same time?  
<br>type: `yesno` · options: `yes`, `no` · per: asked once · done when: `{"rule": "one_of", "options": ["yes", "no"]}` · fills: `roles.multi_role_per_person`
<br>*Why: Asked once, not per role. Decides single-select vs multi-select role assignment — a visible difference.*

**P.01** — In one sentence, who is a '${role}' — what kind of person holds this role?  
<br>type: `text` · done when: `{"rule": "non_empty"}` · fills: `role.{r}.description`
<br>*Why: Context only. Never a build-spec source by itself.*

**P.02** — Can a '${role}' see other people's private information anywhere in the app (personal settings, contact details, private notes)?  
<br>type: `yesno` · options: `yes`, `no` · done when: `{"rule": "one_of", "options": ["yes", "no"]}` · fills: `role.{r}.sees_private_data`

**P.03** — Can a '${role}' see or change billing and payment details?  
<br>type: `yesno` · options: `yes`, `no` · asked if: A.09 = yes · done when: `{"rule": "one_of", "options": ["yes", "no"]}` · fills: `role.{r}.billing_access`

**P.04** — Who can give someone the '${role}' role, or take it away?  
<br>type: `roles` · done when: `{"rule": "roles_min1"}` · fills: `role.{r}.assignable_by`


## Part R — Records

*(repeats once per confirmed **record**)*

**R.01** — What does a '${record}' represent, in one sentence?  
<br>type: `text` · done when: `{"rule": "non_empty"}` · fills: `record.{r}.purpose`

**R.02** — What information does a '${record}' store? For each item: what kind is it, is it required, must it be unique, and (for a list choice) what are the options / (for a link) which record does it link to?  
<br>type: `structured` · visual: `form_builder` · done when: `{"rule": "fields_list", "min": 1, "type_options": "FIELD_TYPES", "per_field_required_keys": ["name", "type", "required", "unique"], "per_field_conditional": {"one_choice": ["options"], "multi_choice": ["options"], "link": ["target_record"], "other": ["custom_rule"]}}` · fills: `record.{r}.fields`
<br>*Why: Handoff never asked for choice options, uniqueness, or the link target. Each one makes two builders diverge.*

**R.03** — Which of those fields is the '${record}'s name — the thing shown in lists, links and messages?  
<br>type: `choice` · options: `<a field from R.02>` · visual: `tap_on_preview` · done when: `{"rule": "field_of", "from": "R.02"}` · fills: `record.{r}.title_field`

**R.04** — Does a '${record}' need a human-readable number or code (like INV-0001)? If so, what format?  
<br>type: `structured` · done when: `{"rule": "structured", "keys": ["needed"], "if": {"needed": "yes", "then_keys": ["format"]}}` · fills: `record.{r}.human_id`

**R.05** — Who can VIEW a '${record}'? For each role: all of them, only their own, only ones linked to something they belong to (say what), or public (no login)?  
<br>type: `roles_scoped` · visual: `access_matrix` · done when: `{"rule": "roles_scoped_min1", "scopes": ["all", "own", "linked", "public"], "if_scope": {"linked": ["via"]}}` · fills: `record.{r}.access.view`
<br>*Why: The handoff's audit resolved the Manager example with a 'their team' scope, then the interview only offered all/own. 'linked' restores it and must name the relation.*

**R.06** — Who can CREATE a '${record}'?  
<br>type: `roles` · visual: `access_matrix` · done when: `{"rule": "roles_min1"}` · fills: `record.{r}.access.create`

**R.07** — Who can EDIT a '${record}'? For each role: any, only their own, or only linked ones?  
<br>type: `roles_scoped` · visual: `access_matrix` · done when: `{"rule": "roles_scoped_min1", "scopes": ["all", "own", "linked"], "if_scope": {"linked": ["via"]}}` · fills: `record.{r}.access.edit`

**R.08** — Who can DELETE a '${record}'? For each role: any, only their own, or only linked ones? ('nobody' is valid)  
<br>type: `roles_scoped` · visual: `access_matrix` · done when: `{"rule": "roles_scoped_min1", "scopes": ["all", "own", "linked"], "if_scope": {"linked": ["via"]}, "or_value": "nobody"}` · fills: `record.{r}.access.delete`

**R.09** — What makes a '${record}' someone's OWN — the person who created it, or the person named in a particular field (which one)?  
<br>type: `structured` · asked if: R.05 has scope own or R.07 has scope own or R.08 has scope own · done when: `{"rule": "structured", "keys": ["basis"], "one_of": {"basis": ["creator", "field"]}, "if": {"basis": "field", "then_keys": ["field"]}}` · fills: `record.{r}.ownership_rule`
<br>*Why: Never asked in the handoff. created_by vs assigned_to is the classic two-builder split.*

**R.10** — Does a '${record}' move through stages over its life (e.g. Draft → Active → Archived)? If so, name them in order.  
<br>type: `structured` · visual: `pipeline_editor` · done when: `{"rule": "structured", "keys": ["has"], "if": {"has": "yes", "then_keys": ["stages"]}}` · fills: `record.{r}.has_lifecycle` · creates: `{"kind": "workflow", "name": "${record} lifecycle", "when": "yes"}`

**R.11** — Is a '${record}' connected to any other record? For each: which record, is it one-to-many or many-to-many, and must the link always exist?  
<br>type: `structured` · visual: `link_diagram` · done when: `{"rule": "relations_list", "min": 0, "keys": ["target", "cardinality", "required"], "one_of": {"cardinality": ["one_to_many", "many_to_many"]}}` · fills: `record.{r}.relations`

**R.12** — When a '${record}' is deleted, what happens to the things connected to it — deleted too, kept but unlinked, or deletion blocked until they're dealt with?  
<br>type: `choice` · options: `delete_too`, `keep_unlinked`, `block` · asked if: R.11 has at least 1 · done when: `{"rule": "one_of", "options": ["delete_too", "keep_unlinked", "block"]}` · fills: `record.{r}.on_delete`

**R.13** — Should old or inactive '${record}'s be archivable (hidden but kept) rather than deleted?  
<br>type: `yesno` · options: `yes`, `no` · done when: `{"rule": "one_of", "options": ["yes", "no"]}` · fills: `record.{r}.archivable`

**R.14** — How long should '${record}' data be kept before it is permanently removed — forever, or a set time after it's archived/closed?  
<br>type: `duration` · done when: `{"rule": "duration_or_forever"}` · fills: `record.{r}.retention` · feeds: OPS

**R.15** — Besides create/edit/delete and moving through stages, are there any other buttons people need on a '${record}' (e.g. duplicate, send, print, mark as paid)? For each: who can press it, what it does, and where the result shows up.  
<br>type: `structured` · visual: `tap_on_preview` · done when: `{"rule": "actions_list", "min": 0, "keys": ["name", "who", "effect", "result_location"], "roles_keys": ["who"]}` · fills: `record.{r}.custom_actions`
<br>*Why: This is where every non-CRUD button gets its number. Handoff derived all actions from CRUD + transitions, so 'Duplicate' could never exist.*


## Part F — Forms

*(repeats once per confirmed **form**)*

**F.01** — What is the '${form}' for, and who fills it out?  
<br>type: `structured` · done when: `{"rule": "structured", "keys": ["purpose", "fillers"], "roles_keys": ["fillers"]}` · fills: `form.{f}.purpose`, `form.{f}.fillers`

**F.02** — Which record does it create or edit? And does it collect anything that is NOT stored on that record? (list those extra items with their kind)  
<br>type: `structured` · visual: `form_builder` · done when: `{"rule": "structured", "keys": ["target"], "optional_keys": ["extra_fields"], "fields_list_key": "extra_fields"}` · fills: `form.{f}.target_record`, `form.{f}.extra_fields`

**F.03** — Does any field only appear depending on another answer? (which field, depends on which answer)  
<br>type: `structured` · visual: `form_builder` · done when: `{"rule": "conditional_list", "min": 0, "keys": ["field", "shown_when"]}` · fills: `form.{f}.conditional_fields`
<br>*Why: Handoff classified this as 'asked only if the owner indicates' but had no prompt that could surface it.*

**F.04** — Can someone save it as a draft and finish later?  
<br>type: `yesno` · options: `yes`, `no` · done when: `{"rule": "one_of", "options": ["yes", "no"]}` · fills: `form.{f}.draft_save`

**F.05** — Right after a successful submit, where should they end up?  
<br>type: `choice` · options: `open_the_record`, `back_to_list`, `stay_with_message`, `another_screen` · visual: `visual_abc` · done when: `{"rule": "one_of", "if_value": {"another_screen": ["screen"]}, "options": ["open_the_record", "back_to_list", "stay_with_message", "another_screen"]}` · fills: `form.{f}.on_success`


## Part FI — Files

*(repeats once per confirmed **file_type**)*

**FI.01** — What is a '${file_type}' used for, and which record is it attached to?  
<br>type: `structured` · done when: `{"rule": "structured", "keys": ["purpose", "parent"]}` · fills: `file.{ft}.purpose`, `file.{ft}.parent_record`

**FI.02** — One per record, or many?  
<br>type: `choice` · options: `one`, `many` · done when: `{"rule": "one_of", "options": ["one", "many"]}` · fills: `file.{ft}.cardinality`

**FI.03** — Who can upload it, and who can view/download it? ('public' allowed for viewing)  
<br>type: `structured` · done when: `{"rule": "structured", "keys": ["uploaders", "viewers"], "roles_keys": ["uploaders", "viewers"]}` · fills: `file.{ft}.uploaders`, `file.{ft}.viewers`

**FI.04** — What kind of file — image, document, spreadsheet, video/audio, or something else (say which formats)?  
<br>type: `choice` · options: `image`, `document`, `spreadsheet`, `media`, `other` · visual: `icon_pick` · done when: `{"rule": "one_of", "if_value": {"other": ["formats"]}, "options": ["image", "document", "spreadsheet", "media", "other"]}` · fills: `file.{ft}.category`

**FI.05** — Roughly how large might these get? (e.g. 10 MB, 500 MB)  
<br>type: `number` · done when: `{"rule": "number"}` · fills: `file.{ft}.max_size_mb`

**FI.06** — If someone uploads a new version, keep the old one (history) or replace it?  
<br>type: `choice` · options: `keep_history`, `replace` · done when: `{"rule": "one_of", "options": ["keep_history", "replace"]}` · fills: `file.{ft}.versioning`

**FI.07** — When the record it belongs to is deleted, delete the file too?  
<br>type: `yesno` · options: `yes`, `no` · done when: `{"rule": "one_of", "options": ["yes", "no"]}` · fills: `file.{ft}.cascade_delete`


## Part FL — Flow — processes and external systems

*(repeats once per confirmed **workflow**)*

Once per confirmed workflow, including every record lifecycle from R.10. Integrations are Flow instances (FL.X questions).

**FL.01** — What starts '${workflow}' — a person doing something (who, doing what), something happening automatically (what), or a schedule (when)?  
<br>type: `structured` · done when: `{"rule": "structured", "keys": ["kind"], "one_of": {"kind": ["person", "event", "schedule"]}, "if_any": {"person": ["who", "action"], "event": ["event"], "schedule": ["schedule"]}, "roles_keys": ["who"]}` · fills: `workflow.{w}.trigger` · feeds: OPS

**FL.02** — What are its stages, in order? Which is the starting stage, and which stage(s) mean it's finished?  
<br>type: `structured` · visual: `pipeline_editor` · done when: `{"rule": "stages", "min": 2, "keys": ["stages", "initial", "terminal"]}` · fills: `workflow.{w}.stages`

**FL.03** — For each move from one stage to the next: is it done by a person (which roles) or does it happen automatically when something happens (what)?  
<br>type: `structured` · visual: `pipeline_editor` · done when: `{"rule": "per_transition", "keys": ["from", "to", "mover"], "mover_one_of": ["roles", "automatic"], "if_mover": {"roles": ["roles"], "automatic": ["event"]}}` · fills: `workflow.{w}.transitions`
<br>*Why: Handoff only allowed a person as mover. 'Order becomes Paid when payment arrives' had no home.*

**FL.04** — Must anything be true before a move is allowed (e.g. can't ship without an address)? For each move: the condition, or none.  
<br>type: `structured` · done when: `{"rule": "per_transition_optional", "keys": ["from", "to", "condition"]}` · fills: `workflow.{w}.preconditions`

**FL.05** — Does any stage need someone's approval before it can move on? Which stage, and which roles approve?  
<br>type: `structured` · visual: `pipeline_editor` · done when: `{"rule": "approvals_list", "min": 0, "keys": ["stage", "approvers"], "roles_keys": ["approvers"]}` · fills: `workflow.{w}.approvals`

**FL.06** — If an approver says no, which stage does it go back to, and can it be resubmitted?  
<br>type: `structured` · asked if: FL.05 has at least 1 · visual: `pipeline_editor` · done when: `{"rule": "structured", "keys": ["back_to", "resubmit"]}` · fills: `workflow.{w}.on_reject`
<br>*Why: Handoff locked 'standard advance/revert' as a default. Back to previous vs back to start vs terminal Rejected are three different products.*

**FL.07** — Can it be cancelled? By whom, and from which stages?  
<br>type: `structured` · visual: `pipeline_editor` · done when: `{"rule": "structured", "keys": ["allowed"], "if": {"allowed": "yes", "then_keys": ["by", "from_stages"]}, "roles_keys": ["by"]}` · fills: `workflow.{w}.cancel`

**FL.08** — Once it reaches a finished stage, what should happen? (e.g. nothing, lock it, send something, create something)  
<br>type: `text` · done when: `{"rule": "non_empty"}` · fills: `workflow.{w}.on_complete`

**FL.09** — From which stage onward, if any, should the record become read-only?  
<br>type: `choice` · options: `<a stage>`, `never` · visual: `tap_on_preview` · done when: `{"rule": "stage_or_never", "from": "FL.02"}` · fills: `workflow.{w}.readonly_from`

**FL.10** — Does any stage have a time limit? Which stage, how long, and what happens when it runs out?  
<br>type: `structured` · visual: `pipeline_editor` · done when: `{"rule": "timeouts_list", "min": 0, "keys": ["stage", "duration", "then"]}` · fills: `workflow.{w}.timeouts` · feeds: OPS

**FL.11** — Should anyone be told when it moves stage? Which moves, who, and by which channel?  
<br>type: `structured` · done when: `{"rule": "notify_list", "min": 0, "keys": ["transition", "recipients", "channels"]}` · fills: `workflow.{w}.stage_notifications` · creates: `{"kind": "notification", "each": true}`
<br>*Why: Owners never list 'tell the assignee on stage change' as a notification in A.15. Asked here so it exists.*


## Part FLX — Flow — external systems

*(repeats once per confirmed **integration**)*

Once per confirmed external system (incl. 'Public API' if A.11 = yes).

**FLX.01** — Why do you need '${integration}' — what is it for?  
<br>type: `text` · done when: `{"rule": "non_empty"}` · fills: `integration.{i}.purpose`

**FLX.02** — What does your app send to it, and what does it get back?  
<br>type: `structured` · done when: `{"rule": "structured", "keys": ["sends", "receives"]}` · fills: `integration.{i}.sends`, `integration.{i}.receives`

**FLX.03** — When does that exchange happen — when something happens in your app (what), on a schedule (when), or when someone presses a button (who)?  
<br>type: `structured` · done when: `{"rule": "structured", "keys": ["kind"], "one_of": {"kind": ["event", "schedule", "manual"]}, "if_any": {"event": ["event"], "schedule": ["schedule"], "manual": ["who"]}}` · fills: `integration.{i}.timing` · feeds: OPS

**FLX.04** — Is it one connection for the whole organisation, or does each person connect their own account?  
<br>type: `choice` · options: `organisation`, `per_user` · done when: `{"rule": "one_of", "options": ["organisation", "per_user"]}` · fills: `integration.{i}.connection_scope`

**FLX.05** — If '${integration}' is unavailable, what should the person see — a blocking message, nothing (it quietly retries later), or the app carries on without it?  
<br>type: `choice` · options: `block_with_message`, `queue_silently`, `continue_without` · done when: `{"rule": "one_of", "options": ["block_with_message", "queue_silently", "continue_without"]}` · fills: `integration.{i}.on_unavailable`


## Part RP — Reports

*(repeats once per confirmed **report**)*

**RP.01** — What question does '${report}' answer for the person reading it?  
<br>type: `text` · done when: `{"rule": "non_empty"}` · fills: `report.{rp}.question`

**RP.02** — Who can view it?  
<br>type: `roles` · done when: `{"rule": "roles_min1"}` · fills: `report.{rp}.viewers`

**RP.03** — Is it a live screen in the app, a downloadable document, or both? And shown as a table, a chart, or both?  
<br>type: `structured` · visual: `visual_abc` · done when: `{"rule": "structured", "keys": ["delivery", "shape"], "one_of": {"delivery": ["screen", "document", "both"], "shape": ["table", "chart", "both"]}}` · fills: `report.{rp}.form`

**RP.04** — What numbers/metrics does it show? (list them)  
<br>type: `list` · done when: `{"rule": "min_items", "n": 1}` · fills: `report.{rp}.metrics`

**RP.05** — For '${metric}': exactly how is it calculated — when does something count, and as at which date?  
<br>type: `text` · asked if: RP.04 any item matches AMBIGUOUS_METRIC_TERMS · per: ambiguous_metric · done when: `{"rule": "non_empty"}` · fills: `report.{rp}.metric.{m}.definition`
<br>*Why: Fires once per metric whose name contains a flagged term. Unanswered = build blocked, never defaulted.*

**RP.06** — What should it be filterable or grouped by, and what date range should it show by default?  
<br>type: `structured` · visual: `report_mockup` · done when: `{"rule": "structured", "keys": ["filters", "default_range"]}` · fills: `report.{rp}.filters`, `report.{rp}.default_range`

**RP.07** — Can it be exported? By whom?  
<br>type: `structured` · done when: `{"rule": "structured", "keys": ["allowed"], "if": {"allowed": "yes", "then_keys": ["by"]}, "roles_keys": ["by"]}` · fills: `report.{rp}.export`

**RP.08** — Should it be sent to anyone automatically on a schedule? Who, how often?  
<br>type: `structured` · done when: `{"rule": "structured", "keys": ["enabled"], "if": {"enabled": "yes", "then_keys": ["recipients", "schedule"]}}` · fills: `report.{rp}.scheduled_delivery` · creates: `{"kind": "notification", "name": "${report} scheduled delivery", "when": "yes"}` · feeds: OPS


## Part N — Notify

*(repeats once per confirmed **notification**)*

Once per confirmed notification, including those created by FL.11 and RP.08 (those arrive pre-filled and only ask what is still empty).

**N.01** — What sends '${notification}' — something happening (what), a time relative to a date on a record (which date, how long before/after), or a fixed schedule?  
<br>type: `structured` · done when: `{"rule": "structured", "keys": ["kind"], "one_of": {"kind": ["event", "relative_to_date", "schedule"]}, "if_any": {"event": ["event"], "relative_to_date": ["record", "date_field", "offset"], "schedule": ["schedule"]}}` · fills: `notification.{n}.trigger` · feeds: OPS

**N.02** — Who receives it — roles, the record's owner, a person named in a field on the record (which), or someone else?  
<br>type: `structured` · done when: `{"rule": "recipients", "min": 1, "kinds": ["roles", "owner", "field", "custom"]}` · fills: `notification.{n}.recipients`

**N.03** — Which channels — email, SMS, push, in-app? (any)  
<br>type: `multi` · options: `email`, `sms`, `push`, `in_app` · visual: `icon_multi` · done when: `{"rule": "subset_min1", "options": ["email", "sms", "push", "in_app"]}` · fills: `notification.{n}.channels`

**N.04** — What should the recipient understand or do after reading it? (exact wording is drafted at build time and sent to you to approve)  
<br>type: `text` · visual: `message_preview` · done when: `{"rule": "non_empty"}` · fills: `notification.{n}.intent`

**N.05** — Can the recipient switch this one off?  
<br>type: `yesno` · options: `yes`, `no` · done when: `{"rule": "one_of", "options": ["yes", "no"]}` · fills: `notification.{n}.opt_out`


## Part B — Billing

*(asked only if A.09 = yes)*

**B.01** — What are you charging for — subscriptions, one-off purchases, usage, or a mix?  
<br>type: `multi` · options: `subscription`, `one_off`, `usage` · done when: `{"rule": "subset_min1", "options": ["subscription", "one_off", "usage"]}` · fills: `billing.model`

**B.02** — Who pays — each person, or a whole organisation at once?  
<br>type: `choice` · options: `person`, `organisation` · done when: `{"rule": "one_of", "options": ["person", "organisation"]}` · fills: `billing.charged_party`

**B.03** — List your plans. For each: name, price, how often it's billed, what's included, and any limits. Is there a free plan?  
<br>type: `structured` · visual: `pricing_builder` · done when: `{"rule": "plans_list", "min": 1, "keys": ["name", "price", "interval", "included", "limits"]}` · fills: `billing.plans`

**B.04** — What currency do you bill in?  
<br>type: `text` · done when: `{"rule": "iso_currency"}` · fills: `billing.currency`

**B.05** — Is there a free trial? How long, and is a card required to start it?  
<br>type: `structured` · asked if: B.01 includes subscription · done when: `{"rule": "structured", "keys": ["enabled"], "if": {"enabled": "yes", "then_keys": ["days", "card_required"]}}` · fills: `billing.trial` · feeds: OPS
<br>*Why: Never asked in the handoff.*

**B.06** — What unit is counted for usage billing, and when is it charged?  
<br>type: `structured` · asked if: B.01 includes usage · done when: `{"rule": "structured", "keys": ["unit", "timing"]}` · fills: `billing.usage_unit`, `billing.usage_charge_timing`

**B.07** — Card only, or can customers also pay by invoice / bank transfer?  
<br>type: `choice` · options: `card_only`, `card_and_invoice` · done when: `{"rule": "one_of", "options": ["card_only", "card_and_invoice"]}` · fills: `billing.payment_methods`
<br>*Why: Locked as 'card via gateway' in the handoff. Pay-by-invoice changes the product (manual reconciliation, dunning), so it is asked.*

**B.08** — If a payment fails: keep access for how many days before restricting? And after repeated failure — suspend, downgrade to free, or cancel?  
<br>type: `structured` · done when: `{"rule": "structured", "keys": ["grace_days", "after_repeated"], "one_of": {"after_repeated": ["suspend", "downgrade", "cancel"]}}` · fills: `billing.on_failure` · feeds: OPS

**B.09** — Can customers change plan themselves? Does an upgrade take effect immediately or at the next cycle? A downgrade?  
<br>type: `structured` · asked if: B.01 includes subscription · done when: `{"rule": "structured", "keys": ["self_serve", "upgrade_timing", "downgrade_timing"], "one_of": {"upgrade_timing": ["immediate", "next_cycle"], "downgrade_timing": ["immediate", "next_cycle"]}}` · fills: `billing.plan_change`

**B.10** — Can customers cancel themselves? Do they keep access until the end of the paid period, or lose it immediately?  
<br>type: `structured` · asked if: B.01 includes subscription · done when: `{"rule": "structured", "keys": ["self_serve", "access_after"], "one_of": {"access_after": ["period_end", "immediate"]}}` · fills: `billing.cancellation`

**B.11** — Are refunds allowed? Who exactly may issue one?  
<br>type: `structured` · done when: `{"rule": "structured", "keys": ["allowed"], "if": {"allowed": "yes", "then_keys": ["by"]}, "roles_keys": ["by"]}` · fills: `billing.refunds`


## Part T — Organisations (tenants)

*(asked only if A.08 = multiple)*

**T.01** — Can one person belong to more than one organisation?  
<br>type: `yesno` · options: `yes`, `no` · done when: `{"rule": "one_of", "options": ["yes", "no"]}` · fills: `tenancy.multi_membership`

**T.02** — How does a new organisation come to exist — someone signs up and creates it, or you (the operator) create it?  
<br>type: `multi` · options: `self_signup`, `operator_created` · done when: `{"rule": "subset_min1", "options": ["self_signup", "operator_created"]}` · fills: `tenancy.creation`

**T.03** — Inside an organisation, which role manages its members and settings?  
<br>type: `choice` · options: `<a confirmed role>` · done when: `{"rule": "role"}` · fills: `tenancy.org_admin_role`
<br>*Why: Never asked in the handoff. Without it, no builder knows who invites people into an org.*

**T.04** — Are the roles the same in every organisation, or can each organisation define its own?  
<br>type: `choice` · options: `same_everywhere`, `per_organisation` · done when: `{"rule": "one_of", "options": ["same_everywhere", "per_organisation"]}` · fills: `tenancy.roles_scope`

**T.05** — Is there an operator role (you) that can see across all organisations? Which role?  
<br>type: `choice` · options: `<a confirmed role>`, `none` · done when: `{"rule": "role_or_none"}` · fills: `tenancy.operator_role`

**T.06** — By default, is everything about an organisation — records, files, reports, billing, workflows — completely separate from the others? If not, what is shared and how?  
<br>type: `structured` · done when: `{"rule": "structured", "keys": ["complete"], "if": {"complete": "no", "then_keys": ["shared"]}}` · fills: `tenancy.isolation`

**T.07** — Can organisations set their own branding (logo, colours)?  
<br>type: `yesno` · options: `yes`, `no` · done when: `{"rule": "one_of", "options": ["yes", "no"]}` · fills: `tenancy.branding`

**T.08** — Can an organisation be suspended or deleted? By whom, and what happens to its members and data?  
<br>type: `structured` · done when: `{"rule": "structured", "keys": ["suspend_allowed", "delete_allowed"], "if_any_yes": ["by", "members", "data"], "roles_keys": ["by"]}` · fills: `tenancy.suspend_delete`


## Part D — Deviations

*(asked only if A.14 has at least 1; repeats once per confirmed **deviation**)*

**D.01** — You said '${deviation}' should work differently from the standard. Which standard behaviour is it replacing, exactly what should happen instead, and which screens/records does it apply to? Everything you don't mention keeps the standard behaviour.  
<br>type: `structured` · done when: `{"rule": "structured", "keys": ["default_id", "behaviour", "scope"], "default_id_in": "DEFAULTS"}` · fills: `deviation.{d}.default_overridden`, `deviation.{d}.behaviour`, `deviation.{d}.scope`


## Part Z — Read-back

Generated by the script from earlier answers. The owner confirms or corrects; nothing new is asked.

**Z.01** — Here is everything the app will do on its own, with nobody clicking: [derived list of scheduled jobs — retention purges, stage time-outs, date-relative reminders, scheduled reports, subscription renewals, trial expiries, integration syncs]. Correct?  
<br>type: `confirm` · done when: `{"rule": "confirmed"}` · fills: `ops.recurring_operations`
<br>*Why: This is the recurring-ops namespace. Each item gets its own OPS-nnn id.*

**Z.02** — Here is every numbered button/action in the app and where its result lands: [derived]. Correct?  
<br>type: `confirm` · visual: `wireframe_walkthrough` · done when: `{"rule": "confirmed"}` · fills: `actions.inventory`

**Z.03** — Here is every screen, who can open it, and what it shows: [derived]. Correct?  
<br>type: `confirm` · visual: `wireframe_walkthrough` · done when: `{"rule": "confirmed"}` · fills: `screens.inventory`


## Field types (closed list for R.02 / AU.02 / F.02)

`short_text`, `long_text`, `whole_number`, `decimal_number`, `money`, `date`, `date_time`, `yes_no`, `one_choice`, `multi_choice`, `email`, `phone`, `url`, `file`, `link`, `other`

`one_choice`/`multi_choice` require the options; `link` requires the target record; `other` requires the exact rule. `whole_number` and `decimal_number` are separate because 'Number' alone makes two builders diverge on decimals.


## Locked system defaults (never asked; override only via Part D)

| ID | Area | Behaviour | Spec fields |
|---|---|---|---|
| `sys_credential_storage` | security | Secrets in an environment vault, never in code or the database. | — |
| `sys_encryption_rest` | security | AES-256 at rest for database and file storage. | — |
| `sys_encryption_transit` | security | TLS everywhere; HttpOnly/Secure/SameSite cookies. | — |
| `sys_database_identifiers` | records | UUIDv4 primary keys on every table. | `record.*.id_strategy` |
| `sys_audit_fields` | records | created_at/updated_at/created_by/updated_by on every table. | `record.*.audit_fields` |
| `sys_request_timeout` | client | 15 s request timeout → transaction aborted, HTTP 504. | — |
| `sys_retry_policy` | flow | Failed external calls retry 3× with exponential backoff + jitter. | `integration.*.retry_policy` |
| `sys_idempotency_webhook` | billing | Payment webhooks signature-verified and processed exactly once. | `billing.webhook_handling` |
| `sys_duplicate_click` | client | Submit buttons disable on click. | — |
| `sys_error_handling` | client | RFC 7807 error bodies; stack traces masked in production. | — |
| `sys_logging` | client | Structured JSON audit log of every mutation and failed authorisation. | — |
| `sys_file_storage` | files | Private object storage for uploads. | `file.*.storage_backend` |
| `sys_file_security_scanning` | files | Async malware scan before a file is marked active. | `file.*.malware_scanning` |
| `sys_file_upload_fail` | files | Failed upload/scan → file marked broken, transaction rolled back, 400. | — |
| `sys_client_isolation` | tenancy | Row-level security enforces organisation isolation in the database. | `tenancy.isolation_mechanism` |
| `sys_backup_recovery` | ops | Nightly encrypted backups, 30-day retention. | — |
| `sys_session_security_protections` | auth | Signed session tokens; CSRF-safe cookie rules. | — |
| `sys_notification_audit` | notify | Every notification logged with channel, recipient, status, retries. | — |
| `sys_notification_retry` | notify | 3 delivery retries then dead-letter. | `notification.*.retry_policy` |
| `sys_report_storage` | reports | Generated documents stored transiently behind 1-hour signed URLs. | — |
| `sys_report_timeout` | reports | Report generation times out at 60 s. | — |
| `sys_api_convention` | technical | One fixed REST convention for every endpoint, verb and envelope. | `api.*` |
| `sys_screen_interaction_pattern` | client | Standard loading / empty / error / success / back / leave-and-return behaviour on every screen. | `screen.*.interaction_states` |
| `sys_field_type_defaults` | records | Each field type carries one standard validation rule and error message. | `record.*.field.*.validation` |
| `sys_report_caching` | reports | Reports regenerate on demand, cached 5 min. | `report.*.cache_policy` |
| `sys_tax_calculation` | billing | Tax computed by the payment gateway from the billing address. | `billing.tax_calculation` |
| `sys_notification_copywriting` | notify | Message wording drafted at build time and approved by the owner before launch; never shipped unseen. | `notification.*.copy_final` |
| `sys_file_type_inference` | files | Allowed formats come from a fixed allow-list per file category. | `file.*.allowed_mimes` |
| `sys_qa_pass_conditions` | qa | Every node's pass/fail check is generated from that node's own answers. | `qa.pass_condition.*` |
| `sys_account_identity` | auth | The email address is the account identity; changing it requires re-verification. | `auth.identity_field` |
| `sys_password_reset` | auth | Self-service reset by emailed link, valid 1 hour. | `auth.self_reset_flow` |
| `sys_mfa_recovery` | auth | One-time recovery codes issued at MFA enrolment. | `auth.mfa_recovery` |
| `sys_profile_self_edit` | auth | Every user can edit their own name, email, password and notification preferences. | `auth.profile_self_service` |
| `sys_suspended_experience` | auth | A suspended user sees a fixed 'account suspended — contact <support contact>' screen and nothing else. | `auth.suspended_screen` |
| `sys_first_admin` | auth | The first super-role account is seeded from the deploy inputs, not created through the app. | `auth.bootstrap_admin` |
| `sys_theme` | client | Light theme only; WCAG 2.1 AA contrast and keyboard access. | `visual.theme`, `visual.accessibility` |
| `sys_locale_formatting` | client | Dates, numbers and currency display in the format of A.13's region; stored in UTC; shown in the viewer's timezone. | `locale.formatting`, `locale.timezone_handling` |
| `sys_concurrent_edit` | records | Last save wins; a user saving over a newer version is warned and shown the newer version. | `record.*.concurrency` |
| `sys_list_behaviour` | records | Every record list is searchable and filterable on its visible fields, sorted newest first, exportable by anyone who can view it. | `record.*.list_behaviour`, `record.*.exportable` |
| `sys_form_failure` | forms | A failed submit shows inline errors and keeps what was typed; forms are single-page; public forms get spam protection. | `form.*.on_failure`, `form.*.layout`, `form.*.spam_protection` |
| `sys_inapp_inbox` | notify | If any notification uses in-app, the app has one notification inbox with read/unread state. | `notify.inbox` |
| `sys_image_handling` | files | Images get thumbnails; downloads are served by signed URL. | `file.*.image_handling` |
| `sys_limit_reached` | billing | Hitting a plan limit shows an upgrade prompt, then blocks the action. | `billing.on_limit_reached` |
| `sys_billing_details` | billing | Card, billing address and tax IDs are collected by the gateway's hosted form; invoices/receipts are the gateway's. | `billing.details_collection`, `billing.invoices` |
| `sys_proration` | billing | Mid-cycle plan changes are prorated by the gateway. | `billing.proration_rule` |
| `sys_org_switcher` | tenancy | A person in several organisations switches with a standard switcher; each organisation has its own timezone setting defaulting to A.13. | `tenancy.switcher`, `tenancy.org_settings` |
| `sys_invite_expiry` | auth | Invitations expire after 7 days and can be re-sent. | `auth.invite_expiry` |

## Derivations (computed; two-builder safe)

| ID | Produces | From | Rule | Safe because |
|---|---|---|---|---|
| D01 | `record.*.field.*.storage_type` | R.02 | Fixed 1:1 map from field type to column type. | Exhaustive, unique per type. |
| D02 | `form.*.fields` | F.02, R.02 | Form fields = target record's fields + extra fields. | Restatement of answers. |
| D03 | `screen.*.contents`, `screen.*.access`, `role.*.visible_screens` | A.15, R.05, R.06, R.07, R.08, FL.03, FL.05 | A screen shows its record/form fields; a role sees a screen if it can view/act on anything on it. | Mechanical union of explicit grants. |
| D04 | `role.*.permitted_actions`, `role.*.forbidden_actions`, `role.*.is_admin` | R.05, R.06, R.07, R.08, R.15, FL.03, FL.05, FL.07, AU.11, AU.12, AU.13, P.04, B.11 | Permitted = every explicit grant; forbidden = everything else (default deny); admin = any user-management grant. | Enumeration, no judgement. |
| D05 | `notification.*.timing` | N.01 | Immediate on event; offset for relative_to_date; cron for schedule. | Read from the owner's own trigger. |
| D06 | `file.*.retention` | R.14, FI.01 | File inherits its parent record's retention. | Direct inheritance. |
| D07 | `report.*.data_source`, `report.*.metric.*.derived_definition` | RP.04, RP.05, R.02 | Unflagged metric = count/sum of the named field; flagged metric = RP.05 text. | Flagged terms never derive. |
| D08 | `workflow.*.transition_graph` | FL.02, FL.03 | Edges exactly as listed in FL.03; nothing added. | Never invents a transition. |
| D09 | `tenancy.role_visibility` | T.05, T.06 | Operator role sees all orgs; everyone else sees their memberships. | Restatement. |
| D10 | `billing.plan_linkage` | B.03 | Each subscription event links to one plan by name. | Restatement. |
| D11 | `ops.recurring_operations.items` | R.14, FL.01, FL.10, FLX.03, N.01, RP.08, B.05, B.08 | Every duration/schedule answer becomes one OPS-nnn job; confirmed in Z.01. | Mechanical collection; owner confirms the list. |
| D12 | `actions.inventory.items` | R.06, R.07, R.08, R.15, FL.03, FL.07, FL.05, F.01 | One numbered action per create/edit/delete grant, custom action, transition, cancel, approve, and form submit. | Enumeration; owner confirms in Z.02. |
| D13 | `screens.inventory.items`, `client.navigation.derived` | A.15, C.06, D03 | One list + one detail screen per record, one per form/report, plus landing per role. | Enumeration; owner confirms in Z.03 / C.07. |
| D14 | `record.*.field.*.storage_type_for_options` | R.02 | Choice options become an enum with the exact listed values. | Restatement. |
| D15 | `qa.generated_tests` | * | For every numbered action and transition: perform it as each role, assert the declared outcome and location. | Definitionally downstream of answers; no LLM in the pass/fail path. |

## Deploy inputs (block 0 — a form, not the interview)

| ID | Needed | When |
|---|---|---|
| DI.01 | Web address (domain) the app will live at | always |
| DI.02 | Sender name and email address for outgoing email | always |
| DI.03 | Support contact shown to users (email or URL) | always |
| DI.04 | Email address of the first super-role account | A.07 = yes |
| DI.05 | Hosting region / data residency (e.g. Australia) | always |
| DI.06 | Payment gateway account credentials | A.09 = yes |
| DI.07 | SMS provider credentials and sender ID | N.03 any instance includes sms |
| DI.08 | OAuth client credentials for each social login chosen | AU.04 includes any of ['google', 'microsoft', 'apple'] |
| DI.09 | Credentials / API keys for each external system | A.15 list non-empty integrations |
| DI.10 | App-store developer accounts | A.06 includes any of ['ios', 'android'] |
| DI.11 | Terms of service and privacy policy documents (or a request to draft them) | AU.14 = yes |

## Ambiguous metric terms (force RP.05)

active, completed, engaged, churn, churned, converted, conversion, retained, retention, revenue, growth, at risk, overdue, on time, utilisation, utilization, average, rate
