#!/usr/bin/env python3
from __future__ import annotations

from typing import Any


def generate_postman_collection(routes: list[dict[str, Any]], title: str) -> dict[str, Any]:
    """Generate Postman collection from routes."""
    items = [
        {
            "name": route.get("name", route["path"]),
            "request": {
                "method": route["method"],
                "url": {
                    "raw": f"{{{{base_url}}}}{route['path']}",
                    "host": ["{{base_url}}"],
                    "path": route["path"].split("/")[1:],
                },
            },
        }
        for route in routes
    ]

    return {
        "info": {
            "name": title,
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": items,
        "variable": [
            {
                "key": "base_url",
                "value": "http://localhost:8000",
            }
        ],
    }
