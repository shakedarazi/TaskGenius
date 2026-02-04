# Production Deployment Guide

This document covers everything needed to deploy TaskGenius to production.

---

## Overview

A "production" deployment of TaskGenius requires:

- Stable HTTPS domain (no temporary tunnels)
- Secure secrets management (no default keys)
- Proper CORS configuration (no wildcards)
- MongoDB persistence
- Telegram webhook mode (not polling)

---

## Environment Variables

Copy `docs/env.production.template` to `.env` in the project root and configure all values.

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `JWT_SECRET_KEY` | Secret for JWT signing. **MUST change from default.** | `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `MONGODB_URI` | MongoDB connection string | `mongodb://mongodb:27017` |
| `CORS_ORIGINS` | Allowed origins (comma-separated, no wildcards) | `https://app.taskgenius.com` |

### Telegram Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | (none) |
| `TELEGRAM_MODE` | `webhook` (prod) or `polling` (dev) | `polling` |
| `TELEGRAM_WEEKLY_SUMMARY_ENABLED` | Enable weekly summaries | `false` |
| `TELEGRAM_WEEKLY_SUMMARY_INTERVAL_SECONDS` | Summary interval | `604800` (7 days) |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode (disables in prod) | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `USE_LLM` | Enable OpenAI integration | `false` |
| `OPENAI_API_KEY` | OpenAI API key | (none) |
| `MODEL_NAME` | OpenAI model name | `gpt-4o-mini` |

---

## Secrets Management

### Rules

1. **Never commit `.env` files** — they are gitignored
2. **Use your deployment platform's secret store** (Railway, Render, AWS Secrets Manager, etc.)
3. **Rotate secrets periodically** — especially `JWT_SECRET_KEY`

### Generating Secure Keys

```bash
# Generate JWT secret
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Database

### MongoDB Configuration

TaskGenius uses MongoDB for persistence. No migrations are required — collections are created automatically.

**Connection:** Set `MONGODB_URI` to your MongoDB instance. In Docker Compose, the default `mongodb://mongodb:27017` works.

**Backups:** Implement regular backups using `mongodump`:

```bash
docker exec taskgenius-mongodb mongodump --out /backup/$(date +%Y%m%d)
```

---

## Networking & HTTPS

### Requirements

- **HTTPS is mandatory** for production
- **Stable domain** required (no temporary tunnels like trycloudflare)
- **Reverse proxy** recommended (nginx, Caddy, or cloud load balancer)

### CORS Configuration

Set `CORS_ORIGINS` to your exact frontend domain(s):

```bash
CORS_ORIGINS=https://app.taskgenius.com,https://www.taskgenius.com
```

**Never use wildcards (`*`) in production.**

### Health Endpoint

The `/health` endpoint returns service status:

```bash
curl https://your-domain.com/health
# {"status": "healthy", "service": "TASKGENIUS Core API", "version": "0.1.0"}
```

Use this for:
- Load balancer health checks
- Docker health checks
- Monitoring systems

---

## Telegram Configuration

### Production Mode

In production, set `TELEGRAM_MODE=webhook` to receive updates via webhook instead of polling.

### Setting Up Webhook

1. **Set environment variable:**
   ```bash
   TELEGRAM_MODE=webhook
   ```

2. **Register webhook with Telegram:**
   ```bash
   curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
     -d "url=https://your-domain.com/telegram/webhook"
   ```

3. **Verify webhook:**
   ```bash
   curl "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"
   ```

### Webhook URL Requirements

- Must be HTTPS
- Must be publicly accessible
- Must be a stable URL (not trycloudflare or ngrok)
- Certificate must be valid (not self-signed)

### Troubleshooting

**Delete existing webhook (if switching to polling):**
```bash
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/deleteWebhook?drop_pending_updates=true"
```

**Common errors:**

| Error | Cause | Fix |
|-------|-------|-----|
| 530 | Cloudflare blocking | Use direct server or configure Cloudflare |
| pending_update_count high | Old updates queued | Delete webhook with `drop_pending_updates=true` |
| certificate error | Invalid SSL | Use valid certificate from Let's Encrypt |

### Weekly Summary Behavior

When `TELEGRAM_WEEKLY_SUMMARY_ENABLED=true`, summaries are sent:
- **Immediately on startup** (first run)
- **Then on interval** (default: every 7 days)

If you don't want summaries on startup, disable the feature or set a very short interval for testing.

---

## Observability

### Logging

Configure logging level via `LOG_LEVEL`:

```bash
LOG_LEVEL=INFO   # Production default
LOG_LEVEL=DEBUG  # For troubleshooting
LOG_LEVEL=WARNING  # Reduce noise
```

Logs are structured with timestamp, logger name, level, and message:

```
2024-01-15 10:30:00 - app.telegram.poller - INFO - Telegram poller started
```

### Recommended Monitoring

- **Health checks:** Poll `/health` endpoint
- **Error tracking:** Integrate Sentry or similar
- **Metrics:** Track request latency, error rates, Telegram message counts

---

## Deployment Steps

### Pre-Deploy Checklist

- [ ] `JWT_SECRET_KEY` changed from default
- [ ] `CORS_ORIGINS` set to production domains (no wildcards)
- [ ] `TELEGRAM_MODE=webhook` set
- [ ] HTTPS configured with valid certificate
- [ ] MongoDB connection string correct
- [ ] Secrets stored securely (not in code)

### Deploy

```bash
# Pull latest code
git pull origin main

# Build and start containers
docker compose up --build -d

# Check health
curl https://your-domain.com/health
```

### Post-Deploy Verification

1. **Health check:**
   ```bash
   curl https://your-domain.com/health
   ```

2. **Telegram webhook test:**
   - Send a message to your bot
   - Check logs: `docker logs taskgenius-core-api`

3. **Authentication test:**
   - Register a user via frontend
   - Login and verify JWT works

4. **CORS test:**
   - Access frontend from production domain
   - Verify API calls succeed

---

## Architecture Reference

```
                              Client
                     React + TypeScript (Vite)
                                |
                                | HTTPS
                                v
    +-----------------------------------------------------------+
    |                     Docker Network                         |
    |                                                            |
    |   +-----------------+         +-------------------+        |
    |   |    core-api     |-------->|  chatbot-service  |        |
    |   |  (public :8000) |         |  (internal :8001) |        |
    |   +--------+--------+         +-------------------+        |
    |            |                                               |
    |            v                                               |
    |   +-----------------+                                      |
    |   |     MongoDB     |                                      |
    |   | (internal:27017)|                                      |
    |   +-----------------+                                      |
    +-----------------------------------------------------------+
```

**Key points:**
- Only `core-api` is exposed publicly (port 8000)
- `chatbot-service` and MongoDB have no external ports
- All secrets via environment variables
