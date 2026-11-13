# Vercel deployment preparation

This repository is configured for Vercel's FastAPI Python runtime. No deployment was started.

## Before creating a deployment

1. Create a managed PostgreSQL database and set `DATABASE_URL` in the Vercel project environment variables (Production and Preview as appropriate). Use the `postgresql://` URL from that provider.
2. On the trusted machine, install the updated dependencies (`pip install -r requirements-local.txt`), set `DATABASE_URL` to the destination, then provision once with `python db/migrate_sqlite_to_postgres.py`. The importer copies the current local demo database (including its 48 shipments and demo contacts) only into an empty destination; it refuses to overwrite populated tables.
3. Add only the secrets/services you want to use as Vercel environment variables: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `ALERT_EMAIL`, `DEMO_ALERTS_ENABLED`; optional `NEWS_API_KEY`, `WEATHER_API_KEY`, `GEMINI_API_KEY`, and `SLACK_WEBHOOK_URL`. Never commit `.env`.
4. Keep `CARRIER_WEBHOOK_URL` empty for a first deployment. The current mock carrier runs only on the developer's computer and is deliberately disabled as a usable carrier when its URL is localhost. A real or separately hosted adapter must be publicly reachable over HTTPS and must confirm a valid safer route before the app updates a shipment.
5. Connect the Git repository to Vercel. Push a feature branch to get a Preview deployment; only merge to the configured production branch when you explicitly want a Production deployment.

## Editing after deployment

Yes. UI and code can continue to change. With Git integration, branch pushes create Preview deployments; merges to the production branch create a new Production deployment. The previous deployment remains available for rollback. Environment-variable changes apply to new deployments, so they also require a redeploy.

## Runtime notes

- The build hook trains both models and bundles the resulting artifacts. The serverless runtime does not run the training pipeline or destructively reseed the database.
- PostgreSQL is required for durable shipment/contact/route updates, alerts, prediction metrics, and dispatch history. Vercel Functions have a read-only application filesystem (apart from temporary `/tmp` storage), so local SQLite and log files are not production persistence.
- The local mock carrier is not part of the deployed service. Do not configure its `127.0.0.1` URL in Vercel.
- Check the Python bundle stays within Vercel's published size/runtime limits after model training.
