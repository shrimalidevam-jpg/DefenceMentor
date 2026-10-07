"""Promote an existing user to administrator from a trusted local shell.

Usage: python -m scripts.create_admin admin@example.com
"""

import argparse

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.notifications import AdminUser
from app.models.enums import UserRole
from app.models.users import User


def promote_user(email: str) -> None:
    database = SessionLocal()
    try:
        user = database.scalar(select(User).where(User.email == email.lower()))
        if user is None:
            raise SystemExit("No user exists for that email. Register the account first.")
        user.role = UserRole.ADMIN
        if database.scalar(select(AdminUser).where(AdminUser.user_id == user.id)) is None:
            database.add(AdminUser(user_id=user.id))
        database.commit()
        print(f"{user.email} is now an administrator.")
    finally:
        database.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Promote an NDA Chatbot user to admin.")
    parser.add_argument("email", help="Email address of an existing user")
    promote_user(parser.parse_args().email)
