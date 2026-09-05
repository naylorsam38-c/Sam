# Visual questions — which interview questions become show-and-tap

The rule: a question goes visual when its answer describes something the customer will eventually **see** (layout, order, placement, style, flow), or when its consequence is easier to **verify by looking** (who sees what, which field appears when). Business facts — retention periods, refund authority, lockout counts, metric definitions — stay as words, because words are exact there and a picture adds nothing.

Nothing about the interview changed: same questions, same gates, same done-rules. The graph now carries a `widget` field on 40 of the 122 questions (the machine map lives in `WIDGETS` inside `build_graph.py`; the widget vocabulary is `WIDGET_VOCAB`, 20 widgets, each one line to remove). The done-rule still decides "answered" — a widget is just a different way to produce the same structured answer, so nothing downstream (validator, templates, checker) changes. All re-verified: graph PASS, self-test PASS, all five templates PASS.

## Why this kills the UI problem

A customer who types "the form should collect name, email and a photo" and a builder who reads it can still ship a form the customer hates. A customer who watched the form assemble itself while they answered R.02 has already approved the UI — the answer and the preview are the same object. The biggest four:

1. **R.02 / AU.02 / F.02 — form builder.** Every field answer instantly renders the real form. Reorder by dragging. Conditional fields (F.03) toggle live.
2. **R.05–R.08 — access matrix with see-it-as-that-role.** After the grid is filled, the widget renders sample records *as each role* and asks "correct?". Permissions stop being abstract before anything is built.
3. **FL.02–FL.10 — pipeline editor.** Stages are pills, moves are arrows, approvals/timeouts are badges on the pill, read-only is a lock the customer taps onto a stage. The whole Flow part is answered on one canvas.
4. **Z.02 / Z.03 — clickable wireframe walkthrough.** The read-back is a tap-through prototype with every numbered button in place. The customer signs off on the UI before the build starts, and your verification script later clicks the same numbers.

## The map (40 questions, 20 widgets)

| Widget | Questions | What the customer does |
|---|---|---|
| form_builder | AU.02, R.02, F.02, F.03 | watches the real form build as they answer; drags order; toggles conditionals live |
| access_matrix | R.05, R.06, R.07, R.08 | roles × verbs grid; then sees sample data rendered as each role and confirms |
| pipeline_editor | R.10, FL.02, FL.03, FL.05, FL.06, FL.07, FL.10 | drags stage pills, draws move arrows, taps an arrow to set who moves it, badges for approval/timeout |
| tap_on_preview | R.03, R.15, FL.09 | taps the title field on a record card; places a custom button and taps where its result lands; taps the stage where the lock starts |
| visual_abc | C.03, C.05, F.05, RP.03 | picks between 2–4 rendered mockups of the same thing |
| wireframe_walkthrough | Z.02, Z.03 | taps through a clickable wireframe of every screen and numbered button; confirms or flags |
| icon_multi | A.06, AU.01, N.03 | taps device / signup-path / channel icons, each with a rendered sample |
| style_board | C.01 | likes/avoids labelled screenshots of real app styles — each tile credits the app it shows |
| chip_select | C.02 | taps three feel words from a curated cloud |
| brand_kit | C.04 | uploads logo, picks colour, sees a live header |
| screen_picker | C.06 | taps the landing screen thumbnail per role |
| screen_map | A.10 | taps locks open/closed on the screen map to set what's public |
| drag_order | C.07 | drags the live nav menu into order |
| card_board | A.15 | edits the proposed inventory as cards per list |
| login_preview | AU.04 | toggles login methods and watches the sign-in screen change |
| link_diagram | R.11 | drags a line between record cards to declare a relationship |
| message_preview | N.04 | reads a rendered sample email/SMS/push and edits the intent under it |
| report_mockup | RP.06 | toggles filter chips and the date range on a rendered report |
| pricing_builder | B.03 | edits plan cards on a live pricing page |
| icon_pick | FI.04 | taps the file-kind icon |

## What deliberately stays text (words are the precise form)

Part 0 and A.01–A.05, A.07–A.09, A.11–A.14, A.16 · Part P (who a role is, boundary yes/nos) · AU.03, AU.05–AU.14 · R.01, R.04, R.09, R.12–R.14 · F.01, F.04 · FI.01–FI.03, FI.05–FI.07 · FL.01, FL.04, FL.08, FL.11 · FLX (all) · N.01, N.02, N.05 · RP.01, RP.02, RP.04, **RP.05 metric definitions** (the whole point is forcing exact words), RP.07, RP.08 · B.01–B.02, B.04–B.11 · Part T · Part D · Z.01 (the recurring-ops list reads better as a list).

## Credits

Style-board tiles show and name the apps whose look they sample — credit rendered on the tile, per `style_board`'s vocabulary entry. The five templates already credit their source apps (Asana, Pipedrive, Acuity Scheduling, Odoo, Xero) in each template JSON's `source_app` field and in `CONFIG_MAP.md`.
