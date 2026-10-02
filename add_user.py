from database import init_db
from user import create_user

SessionLocal = init_db()
db = SessionLocal()

print("--- PrideChat User Creator ---")
username = input("Username daalo (jaise alexa): ")
password = input("Password daalo (jaise 1): ")

try:
    user = create_user(username, password, db)
    print(f"\n[+] Success! User '{username}' successfully ban gaya hai.")
except Exception as e:
    print(f"\n[!] Error: {e}")
finally:
    db.close()