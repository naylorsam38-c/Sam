# APP LIBRARY MANIFEST

Not a physical copy of the app library — see `ACTIVE_FILE_REGISTER.md` for why relocating it was deliberately not attempted (it would break `consolidate_library.py`/`run_full_verification.py`/`build_batch.py`'s fixed relative-path references). This manifest is the pointer: where the real, active, verified apps actually live.

**Verified against:** `verification/verification_result.json`, current run — `overall: PASS`.

## 43 canonical apps — `verification/library_build/<slug>/library/APP-001/`, consolidated into `OUTPUT_LIBRARY/<slug>/`

todo_list, note_taking, habit_tracker, calendar_and_scheduling, expense_tracker, invoicing, accounting_ledger, crm, helpdesk_ticketing, payroll, project_management, team_chat, video_conferencing, email_client, file_storage_and_sync, collaborative_document_editor, spreadsheet, form_builder_and_survey, e_commerce_storefront, multi_vendor_marketplace, auction, food_delivery, ride_hailing, parcel_tracking, appointment_booking, property_rental, event_ticketing, restaurant_pos, inventory_and_warehouse, fleet_tracking, dating, social_feed, photo_sharing, short_video_feed, music_streaming, video_streaming, podcast, fitness_tracking, meditation_and_wellbeing, language_learning, online_course_lms, quiz_and_flashcards, recipe_and_meal_planning.

**Status:** 43/43 READY (`verification_result.json.sections.canonical_apps`).

## 6 composed apps — `verification/library_build/<slug>/`, driven by `verification/new_app_*.py`

new_app_event_board, new_app_fitness_challenge, new_app_course_enrollment, new_app_recipe_box, new_app_bug_tracker, new_app_volunteer_shift_signup.

**Status:** 6/6 true (`verification_result.json.sections.new_composed_apps`).

## 15 coverage-expansion apps — `verification/coverage_expansion/library_build/<slug>/`

ai_creative_studio, developer_platform, digital_publishing, document_storage_demo, government_portal, guest_and_service_demo, identity_and_access_demo, medical_patient_portal, multiplayer_game, navigation_delivery, personal_finance, recruitment_platform, secure_vault, travel_planner, weather_alerts.

**Status:** 15/15 pass (`verification_result.json.sections.coverage_expansion_apps`).

## Aggregate figures (current, live)

300 capabilities across 49 projects, dependency graph CLEAN (0/0/0/0), 329/329 full-library stress test, 30/30 functional tests, `note_taking_pilot_security_tests.py` 64/64 (re-run separately, not one of the 8 orchestrated sections).
