# Setup

1. Clone the repo and `cd` into it.
2. Copy the env template: `cp .env.example .env`
3. Edit `.env` with your local values.
4. Start the dev stack: `make build-dev`
5. Open [http://localhost:8000](http://localhost:8000).

**Useful commands**

- `make up` — run in the background
- `make down` — stop containers
- `make lint` — lint with ruff
- `make fix` — auto-fix lint issues and format
- `make type` — type-check with mypy
- `make test` — run tests (requires [uv](https://docs.astral.sh/uv/) locally)

PS: you need to be in the root folder to use make commands
