# Integration Definition Validator

Integration Definition Validator is a stateless FastAPI service that reviews a JSON
definition of an API integration before implementation or release. It performs static
checks only: the service never calls the described API and does not persist the submitted
definition or report.

## Live deployment

The verified public deployment runs on Google Cloud Run:

- **Service:** [Cloud Run deployment][live-service]
- **Swagger UI:** [interactive API documentation][live-swagger]
- **ReDoc:** [alternative API documentation][live-redoc]
- **Health check:** [`GET /health`][live-health]
- **OpenAPI schema:** [`/openapi.json`][live-openapi]

> The demo is public and has no application-level authentication. Submit credential
> references such as `MONDAY_API_TOKEN`, never real secrets or tokens.

## Why this exists

Integration definitions tend to encode the same failure modes repeatedly: secrets pasted
into configuration, insecure URLs, retries on unsafe operations, undocumented parameters,
and missing failure tests. Catching those problems in a consistent validation step makes
design reviews faster and gives CI pipelines an objective report: findings, a 0–100 score,
a letter grade, and a pass/fail signal.

## How it works

```text
JSON request
  -> Pydantic structural validation
  -> independent semantic rules
  -> score and severity summary
  -> JSON report
```

Pydantic handles structural schema validation first. Structurally valid requests then run
through 29 semantic rules across five reporting categories:

| Category | Examples |
| --- | --- |
| API design | unique command/input names, snake_case, path parameters, 2xx responses |
| Security | HTTPS, secret references, auth completeness, least-privilege scopes |
| Reliability | bounded timeouts, retry policy, idempotency, retryable status codes |
| Testing | success, authentication failure, server error, and timeout scenarios |
| Documentation | descriptions, output definitions, and ownership |

The score starts at 100. Each critical, error, warning, or info finding deducts 25, 15, 5,
or 0 points respectively, with a floor of zero. Grades are A (90–100), B (80–89), C
(70–79), D (60–69), and F (below 60). A definition is `valid` when it has no critical or
error findings; warnings still reduce its score and grade.

## API

The public service exposes [Swagger UI][live-swagger], [ReDoc][live-redoc], and the raw
[OpenAPI schema][live-openapi]. When running locally, the same resources are available at
`http://localhost:8080/docs`, `http://localhost:8080/redoc`, and
`http://localhost:8080/openapi.json`.

[![Swagger UI served by the public Cloud Run deployment](docs/swagger-ui.png)][live-swagger]

_Swagger UI captured from the verified public Cloud Run deployment._

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Redirect to Swagger UI |
| `GET` | `/health` | Service health and version |
| `POST` | `/api/v1/validate` | Validate an integration definition |
| `GET` | `/api/v1/rules` | List every enabled validation rule |

Semantic problems return `200 OK` with findings. A body that does not match the Pydantic
schema returns a structured `422 Unprocessable Entity`; a body larger than 256 KiB returns
HTTP `413`. Unexpected failures return a sanitized `500 Internal Server Error`
without exposing internals.

### Example request

The complete examples are in
[`examples/valid_integration.json`](examples/valid_integration.json) and
[`examples/invalid_integration.json`](examples/invalid_integration.json).

From the repository root, call the public deployment with:

```bash
SERVICE_URL="https://integration-definition-validator-617920646485.europe-west1.run.app"
curl --request POST "${SERVICE_URL}/api/v1/validate" \
  --header "Content-Type: application/json" \
  --data @examples/valid_integration.json
```

Use `http://localhost:8080` as `SERVICE_URL` to call a local instance instead.

The shortened request below is illustrative. It omits some tests and output documentation,
so it can produce warnings even though the complete valid example produces a perfect report.

```json
{
  "name": "Monday Board Integration",
  "description": "Reads and creates items in monday.com boards",
  "version": "1.0.0",
  "base_url": "https://api.monday.com/v2",
  "owner": "ai-integration-team",
  "authentication": {
    "type": "oauth2_client_credentials",
    "credential_references": ["MONDAY_CLIENT_ID", "MONDAY_CLIENT_SECRET"],
    "token_url": "https://auth.monday.com/oauth/token",
    "scopes": ["boards:read", "boards:write"]
  },
  "timeout_seconds": 15,
  "retry_policy": {
    "enabled": true,
    "max_attempts": 3,
    "backoff_strategy": "exponential",
    "retry_on_status_codes": [429, 500, 502, 503, 504]
  },
  "commands": [
    {
      "name": "get_board_items",
      "description": "Returns items from a board",
      "method": "POST",
      "path": "/v2",
      "inputs": [],
      "outputs": [],
      "expected_status_codes": [200],
      "idempotency_key_supported": true,
      "test_cases": []
    }
  ]
}
```

### Example response

The complete valid example produces a perfect report (apart from the generated identifier
and timestamp):

```json
{
  "validation_id": "36e83a67-c988-4e9a-b0da-a44d71e338ad",
  "validated_at": "2026-08-04T12:00:00Z",
  "integration_name": "Monday Board Integration",
  "valid": true,
  "score": 100,
  "grade": "A",
  "summary": {
    "critical": 0,
    "errors": 0,
    "warnings": 0,
    "info": 0
  },
  "findings": []
}
```

Identifiers and timestamps are generated for each request.

## Run locally

Python 3.12 or newer is required.

```bash
python -m venv .venv
```

Activate the environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

```bash
source .venv/bin/activate
```

Then install and start the service:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

Optional CORS origins are read from a comma-separated environment variable:

```powershell
$env:CORS_ALLOWED_ORIGINS = "https://portal.example.com,https://ci.example.com"
```

```bash
export CORS_ALLOWED_ORIGINS="https://portal.example.com,https://ci.example.com"
```

## Quality checks

```bash
ruff check app tests
ruff format --check app tests
mypy app
pytest --cov=app --cov-report=term-missing --cov-fail-under=85
docker build --tag integration-definition-validator:ci .
```

These checks also run through [GitHub Actions](.github/workflows/ci.yml) on pushes and pull
requests. The suite exercises every validation rule in both passing and failing states,
endpoint behavior, scoring, schema errors, exception sanitization, and operational
collection/body limits.

## Docker

```bash
docker build --tag integration-definition-validator:local .
docker run --rm --publish 8080:8080 integration-definition-validator:local
```

To use another host port while keeping the container on Cloud Run's conventional port:

```bash
docker run --rm --publish 9000:8080 integration-definition-validator:local
```

The image runs as a non-root user and reads its listening port from `PORT` (default 8080).

## Manual deployment to Google Cloud Run

The following source deployment uses the repository Dockerfile. Run it from the repository
root, replace `YOUR_PROJECT_ID`, enable billing, and use an account with permission to deploy
Cloud Run services and submit Cloud Build jobs:

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
gcloud run deploy integration-definition-validator --source . --region europe-west1 --allow-unauthenticated --min 0 --max 3
```

After deployment, obtain the assigned service URL and open its `/docs` path:

```bash
SERVICE_URL="$(gcloud run services describe integration-definition-validator --region europe-west1 --format='value(status.url)')"
echo "${SERVICE_URL}/docs"
```

PowerShell equivalent:

```powershell
$serviceUrl = gcloud run services describe integration-definition-validator --region europe-west1 --format="value(status.url)"
"$serviceUrl/docs"
```

The current deployment is verified at [the live Swagger UI][live-swagger].

### Continuous deployment from GitHub

For automatic deployments, connect the
[`rankes96-dev/Integration-Definition-Validator` repository][github-repository] to Cloud
Run through Cloud Build, select the `main` branch, and build from `/Dockerfile`. The
repository's GitHub Actions workflow runs quality checks; the deployment trigger is managed
separately in Google Cloud.

## Security and operational behavior

- Request bodies are limited to 256 KiB.
- A definition may contain at most 100 commands, 100 inputs and 100 outputs per command,
  and 50 test cases per command.
- Application validation logs contain the validation ID, integration name, score, finding
  counts, and duration. They omit request bodies, findings, and credential values; Google
  Cloud may additionally retain platform-level request logs.
- The public demo is unauthenticated, so submitted definitions must contain references to
  credentials rather than credential values.
- The service has no database, persistence layer, user authentication, or outbound HTTP
  client.
- CORS is disabled unless explicitly configured.

## Known limitations

- Input is JSON only; YAML and uploaded files are outside the MVP.
- The service validates a purpose-built integration model, not OpenAPI documents.
- Secret detection is heuristic and can produce both false positives and false negatives.
- Rules are currently fixed in code and cannot be customized per organization.
- No validation history, UI dashboard, user authentication, rate limiting, or live API
  probing is included.

## Future improvements

Potential extensions include JSON/YAML file upload, OpenAPI import, configurable policies
and score thresholds, HTML reports, automatic validation of integration-definition files in
pull requests, and optional validation history. Those additions should preserve the current
engine's deterministic, no-outbound default behavior.

## License

Released under the [MIT License](LICENSE).

[github-repository]: https://github.com/rankes96-dev/Integration-Definition-Validator
[live-health]: https://integration-definition-validator-617920646485.europe-west1.run.app/health
[live-openapi]: https://integration-definition-validator-617920646485.europe-west1.run.app/openapi.json
[live-redoc]: https://integration-definition-validator-617920646485.europe-west1.run.app/redoc
[live-service]: https://integration-definition-validator-617920646485.europe-west1.run.app
[live-swagger]: https://integration-definition-validator-617920646485.europe-west1.run.app/docs
