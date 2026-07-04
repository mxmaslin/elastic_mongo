# Vision — Stream Catalog API

## Зачем этот проект

Демонстрация уверенного владения **MongoDB** и **Elasticsearch** для
работодателей: в коммерческом стаже этих СУБД не было, поэтому резюме честно
ссылается на этот репозиторий вместо приписанного опыта.

Ссылка из резюме: `github.com/mxmaslin/elastic_mongo`
(footnote в `~/_job-search/resume_ru2.md` / senior / публичных версиях).

## Что показывает

| Тема | Где смотреть |
|------|--------------|
| Документная модель, atomic upsert, optimistic concurrency | `infrastructure/mongo/`, агрегаты в `domain/` |
| Полнотекстовый поиск: multi_match, fuzziness, фильтры, highlight, пагинация | `infrastructure/es/`, `application/search_service.py` |
| Консистентность Mongo → ES: best-effort + reindex, честный trade-off про outbox/CDC | README «Consistency & fault tolerance» |
| DDD-слои, ports & adapters | `src/stream_catalog/` |
| Тестовая культура | 59 unit + 36 integration/e2e; uuid-изоляция прогонов |
| CI | GitHub Actions: lint → unit → integration → docker build |

## Критерий готовности

Публичный репозиторий с зелёным CI, на который не стыдно дать ссылку в отклике
и который выдерживает вопросы техсобеса по Mongo/ES.
