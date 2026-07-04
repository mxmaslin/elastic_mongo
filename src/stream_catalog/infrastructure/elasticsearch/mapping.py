"""Index settings and mapping for the ``titles`` search index."""

from __future__ import annotations

from typing import Any

TITLES_MAPPING: dict[str, Any] = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,  # single-node demo; raise in a real cluster
    },
    "mappings": {
        "dynamic": "strict",
        "properties": {
            "name": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "description": {"type": "text"},
            "cast": {"type": "text"},
            "genres": {"type": "keyword"},
            "type": {"type": "keyword"},
            "release_year": {"type": "integer"},
            "rating": {"type": "float"},
            "updated_at": {"type": "date"},
        },
    },
}
