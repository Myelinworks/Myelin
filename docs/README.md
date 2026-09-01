# Backend Documentation

## PDF Generation

- **[PDF Migration Guide](./pdf-migration.md)**: Complete guide for migrating from frontend jsPDF to backend Playwright PDF generation. Includes architecture overview, API reference, frontend migration steps, and troubleshooting.

## Architecture

The backend uses:
- **FastAPI** for HTTP API
- **SQLAlchemy** for database access (PostgreSQL)
- **Alembic** for migrations
- **Playwright** for PDF generation (headless Chromium)
- **Redis** for caching
- **uv** for Python package management

See [../README.md](../README.md) for project-level documentation.
