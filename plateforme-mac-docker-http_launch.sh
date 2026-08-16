python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
set -a
source .env.mac.local
set +a
.venv/bin/python scripts/run_kestra_tests.py --kestra-live --report test-reports/mac-docker-http.md