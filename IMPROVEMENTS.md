# Рекомендации по развитию (не реализовано)

Приоритетные улучшения для следующих итераций — без изменения текущего стабильного контракта.

## Архитектура

- **Request ID middleware** — `X-Request-ID` в логах и ответах (как в marketplace-pipeline) для трассировки в Kibana/Grafana.
- **Structured logging** — JSON-логи с полями `request_id`, `user_id`, `title_id` в production.
- **OpenTelemetry** — spans на Mongo/ES вызовы для latency breakdown.

## DDD

- Выделить **domain events** (`TitleCreated`, `WatchlistUpdated`) для eventual consistency между Mongo и ES вместо синхронного dual-write в use case (сейчас допустимо для demo).
- **Anti-corruption layer** для ES mapping — отдельный mapper в `infrastructure/elasticsearch/`.

## API

- Rate limiting на `/search` (защита от abuse).
- ETag / If-Match на PUT title для явного optimistic locking в HTTP (сейчас version только в domain).

## CI/CD

- Публикация образа в registry по tag `main`.
- Smoke test после deploy: `GET /health/ready`.

## Безопасность

- API key или mTLS для admin/reindex endpoints в production.
