from pathlib import Path
from wordlist_generator.login import AdminAuthenticator, DEFAULT_USERNAME, DEFAULT_PASSWORD
p=Path('wordlist_generator/test_auth.json')
if p.exists():
    p.unlink()
print('temp auth path:', p)
auth=AdminAuthenticator(p)
print('auth file created:', p.exists())
try:
    ok=auth.validate(DEFAULT_USERNAME, DEFAULT_PASSWORD)
    print('validate ok:', ok)
except Exception as e:
    print('validate failed:', e)
# cleanup
try:
    p.unlink()
    print('temp auth removed')
except Exception as e:
    print('cleanup failed:', e)
