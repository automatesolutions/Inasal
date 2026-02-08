"""Quick test script to verify phone number validation"""
import re

PH_PHONE_REGEX = re.compile(r'^(\+?63|0)?9\d{9}$')

test_cases = [
    ("639123456789", True, "63 prefix without +"),
    ("09123456789", True, "0 prefix"),
    ("9123456789", True, "10 digits starting with 9"),
    ("+639123456789", True, "+63 prefix"),
    ("1234567890", False, "Doesn't start with 9"),
    ("912345678", False, "Too short"),
    ("", False, "Empty string"),
]

print("Testing Phone Number Validation")
print("=" * 60)
for phone, expected, description in test_cases:
    cleaned = re.sub(r'[\s-]', '', phone)
    result = bool(PH_PHONE_REGEX.match(cleaned))
    status = "✅" if result == expected else "❌"
    print(f"{status} {phone:20} -> {result:5} ({description})")

print("\n" + "=" * 60)
print("All tests should show ✅ if validation is working correctly")
