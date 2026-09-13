#!/usr/bin/env python3
"""build_one.py <slug> — generate one app_defs.py app, drop in the real,
fixed build.py, disable layer three (nothing here is expected to need
repair), and run it as a real subprocess. Prints build.py's own real output
verbatim and exits with its exit code."""
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import app_defs  # noqa: E402

ROOT = HERE / "library_build"
ROOT.mkdir(exist_ok=True)

BUILDERS = {
    "todo_list": app_defs.build_todo_list,
    "note_taking": app_defs.build_note_taking,
    "habit_tracker": app_defs.build_habit_tracker,
    "calendar_and_scheduling": app_defs.build_calendar,
    "expense_tracker": app_defs.build_expense_tracker,
    "invoicing": app_defs.build_invoicing,
    "accounting_ledger": app_defs.build_accounting_ledger,
    "crm": app_defs.build_crm,
    "helpdesk_ticketing": app_defs.build_helpdesk,
    "payroll": app_defs.build_payroll,
    "project_management": app_defs.build_project_management,
    "team_chat": app_defs.build_team_chat,
    "spreadsheet": app_defs.build_spreadsheet,
    "form_builder_and_survey": app_defs.build_form_builder,
    "parcel_tracking": app_defs.build_parcel_tracking,
    "appointment_booking": app_defs.build_appointment_booking,
    "event_ticketing": app_defs.build_event_ticketing,
    "restaurant_pos": app_defs.build_restaurant_pos,
    "inventory_and_warehouse": app_defs.build_inventory,
    "property_rental": app_defs.build_property_rental,
    "fleet_tracking": app_defs.build_fleet_tracking,
    "dating": app_defs.build_dating,
    "social_feed": app_defs.build_social_feed,
    "photo_sharing": app_defs.build_photo_sharing,
    "quiz_and_flashcards": app_defs.build_quiz_and_flashcards,
    "recipe_and_meal_planning": app_defs.build_recipe_and_meal_planning,
    "language_learning": app_defs.build_language_learning,
    "online_course_lms": app_defs.build_online_course_lms,
    "file_storage_and_sync": app_defs.build_file_storage,
    "collaborative_document_editor": app_defs.build_doc_editor,
    "e_commerce_storefront": app_defs.build_ecommerce,
    "multi_vendor_marketplace": app_defs.build_marketplace,
    "auction": app_defs.build_auction,
    "food_delivery": app_defs.build_food_delivery,
    "ride_hailing": app_defs.build_ride_hailing,
    "fitness_tracking": app_defs.build_fitness_tracking,
    "meditation_and_wellbeing": app_defs.build_meditation,
    "email_client": app_defs.build_email_client,
    "video_conferencing": app_defs.build_video_conferencing,
    "short_video_feed": app_defs.build_short_video_feed,
    "music_streaming": app_defs.build_music_streaming,
    "video_streaming": app_defs.build_video_streaming,
    "podcast": app_defs.build_podcast,
}


def main():
    slug = sys.argv[1]
    if slug not in BUILDERS:
        print(f"no builder registered for {slug!r}; known: {sorted(BUILDERS)}")
        return 2
    BUILDERS[slug](ROOT)
    project = ROOT / slug
    build_py_src = (HERE.parent / "build.py").read_text()
    build_py_src = build_py_src.replace("ALLOW_LAYER3 = True", "ALLOW_LAYER3 = False")
    (project / "build.py").write_text(build_py_src)
    res = subprocess.run([sys.executable, "build.py"], cwd=str(project))
    return res.returncode


if __name__ == "__main__":
    raise SystemExit(main())
