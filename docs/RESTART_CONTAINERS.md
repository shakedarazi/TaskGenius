# TaskGenius - Container Restart Commands

Run these commands from the project root directory.

## After Recent Changes (Both Services Modified)

```bash
docker compose build chatbot-service core-api
docker compose up -d chatbot-service core-api
```

## Quick Restart (chatbot-service only)

```bash
docker compose build chatbot-service
docker compose up -d chatbot-service
```

## Quick Restart (core-api only)

```bash
docker compose build core-api
docker compose up -d core-api
```

## Full Restart (all services)

```bash
docker compose build
docker compose up -d
```

## View Logs (to verify changes)

```bash
# Follow chatbot-service logs
docker compose logs -f chatbot-service

# Follow core-api logs
docker compose logs -f core-api

# Follow all logs
docker compose logs -f
```

## Force Rebuild (if caching issues)

```bash
docker compose build --no-cache chatbot-service core-api
docker compose up -d chatbot-service core-api
```
