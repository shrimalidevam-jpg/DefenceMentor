# Tests

Backend API, curriculum, diagnostic, learning and mastery tests live in `backend/tests`.

Run them from the `backend` directory:

```powershell
$env:DATABASE_URL="sqlite://"
python -m unittest discover -s tests -p "test_*.py" -v
```

Structure will include:
- Backend unit & integration tests
- API tests
- Frontend tests
- Adaptive engine tests
