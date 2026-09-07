"""Create the initial (and, for this single-user system, only) admin user.

Usage:
    PYTHONPATH=libs/core:. python3 database/seeds/seed_admin.py --username sam --password <pw>

Idempotent: re-running with the same username updates the password instead
of creating a duplicate. Never invents a default password — if one is not
supplied and WORKSTATION_ADMIN_PASSWORD is not set, the script fails with
a clear error rather than guessing a "secure enough" value.
"""

from __future__ import annotations

import argparse
import os
import sys

from workstation_core.db import init_db, session_scope
from workstation_core.models_orm import User
from workstation_core.security import hash_password


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", default=os.environ.get("WORKSTATION_ADMIN_USERNAME", "admin"))
    parser.add_argument("--password", default=os.environ.get("WORKSTATION_ADMIN_PASSWORD"))
    args = parser.parse_args()

    if not args.password:
        print(
            "ERROR: no password provided. Pass --password or set "
            "WORKSTATION_ADMIN_PASSWORD. Refusing to fabricate a default credential.",
            file=sys.stderr,
        )
        return 1

    init_db()
    with session_scope() as db:
        user = db.query(User).filter(User.username == args.username).one_or_none()
        if user is None:
            user = User(username=args.username, password_hash=hash_password(args.password))
            db.add(user)
            print(f"Created user '{args.username}'.")
        else:
            user.password_hash = hash_password(args.password)
            print(f"Updated password for existing user '{args.username}'.")
        db.commit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
