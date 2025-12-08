"""
Script to check production security settings
Run this to verify all security settings are correct for production
"""
import os
import sys
import django

# Set environment to production mode for testing
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
os.environ['DEBUG'] = 'False'
os.environ['SECRET_KEY'] = 'test-secret-key-for-security-check-only'

django.setup()

from django.conf import settings
from django.core.management import call_command

print("=" * 60)
print("PRODUCTION SECURITY CHECK")
print("=" * 60)
print()

# Check current settings
print("Current Settings:")
print(f"  DEBUG: {settings.DEBUG}")
print(f"  SECURE_SSL_REDIRECT: {settings.SECURE_SSL_REDIRECT}")
print(f"  SESSION_COOKIE_SECURE: {settings.SESSION_COOKIE_SECURE}")
print(f"  CSRF_COOKIE_SECURE: {settings.CSRF_COOKIE_SECURE}")
print(f"  SECURE_HSTS_SECONDS: {settings.SECURE_HSTS_SECONDS}")
print(f"  SECURE_HSTS_INCLUDE_SUBDOMAINS: {settings.SECURE_HSTS_INCLUDE_SUBDOMAINS}")
print(f"  SECURE_HSTS_PRELOAD: {settings.SECURE_HSTS_PRELOAD}")
print()

# Run Django security check
print("Running Django security check...")
print("-" * 60)
try:
    call_command('check', '--deploy')
    print()
    print("✓ All security checks passed!")
except SystemExit as e:
    if e.code == 0:
        print()
        print("[OK] All security checks passed!")
    else:
        print()
        print("[ERROR] Some security issues found. See above.")
        sys.exit(1)

print()
print("=" * 60)
print("SECURITY CHECK COMPLETE")
print("=" * 60)
