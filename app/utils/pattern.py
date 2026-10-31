import re

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
PHONE_REGEX = re.compile(r"^\+?[0-9]{7,15}$")
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_-]{3,64}$")


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_REGEX.match(email.strip()))


def is_valid_phone(phone: str) -> bool:
    return bool(PHONE_REGEX.match(phone.strip()))


def is_valid_username(username: str) -> bool:
    return bool(USERNAME_REGEX.match(username.strip()))
