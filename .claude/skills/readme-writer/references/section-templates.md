# README Section Templates

## Installation Section Patterns

### Python (uv)
```markdown
## Installation

```bash
# Clone repository
git clone <repo-url>
cd <project-name>

# Install dependencies
uv sync

# Activate environment
source .venv/bin/activate
```
```

### Python (pip)
```markdown
## Installation

```bash
pip install -r requirements.txt
```
```

### Node.js
```markdown
## Installation

```bash
npm install
# or
yarn install
```
```

## Configuration Section Patterns

### Environment Variables
```markdown
## Configuration

Create `.env` file:

```env
DATABASE_URL=postgresql://user:pass@localhost/db
API_KEY=your_api_key_here
SECRET_KEY=your_secret_key
```

| Variable | Required | Description |
|----------|----------|-------------|
| DATABASE_URL | Yes | PostgreSQL connection string |
| API_KEY | Yes | External API key |
| SECRET_KEY | No | Session encryption key (auto-generated if not set) |
```

## Usage Section Patterns

### CLI Application
```markdown
## Usage

```bash
# Basic usage
<command> <args>

# With options
<command> --option value
```
```

### Web Server
```markdown
## Usage

Start the server:

```bash
uvicorn src.server:app --reload --port 8000
```

Access at http://localhost:8000

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/resource | Create resource |
| GET | /api/resource/:id | Get resource |
```

## Architecture Section Pattern

```markdown
## Architecture

```
src/
├── server.py      # FastAPI application entry
├── models.py      # Data models
├── services/      # Business logic
└── utils/         # Helper functions
```

### Key Components

| Component | Purpose |
|-----------|---------|
| `server.py` | HTTP request handling |
| `services/auth.py` | Authentication logic |
```

## Development Section Pattern

```markdown
## Development

### Run Tests
```bash
pytest -v
```

### Lint
```bash
black src/
```

### Database Migrations
```bash
alembic upgrade head
```
```
