#!/usr/bin/env python3
from __future__ import annotations

from typing import Any


def generate_openapi_spec(routes: list[dict[str, Any]], title: str, version: str) -> dict[str, Any]:
    """Generate OpenAPI 3.0 spec from routes."""
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": title,
            "version": version,
        },
        "paths": {},
    }

    for route in routes:
        path = route["path"]
        method = route["method"].lower()

        if path not in spec["paths"]:
            spec["paths"][path] = {}

        spec["paths"][path][method] = {
            "summary": route.get("name", "Endpoint"),
            "description": route.get("description", ""),
            "responses": {
                "200": {
                    "description": "Success",
                }
            },
        }

    return spec
