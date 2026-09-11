#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import pandas as pd
except ImportError:
    pd = None


def load_and_profile(file_path: Path) -> tuple[Any, dict]:
    """Load CSV/Excel and return basic profile without sending raw data to Claude."""
    if not pd:
        return None, {}

    try:
        if file_path.suffix == ".csv":
            df = pd.read_csv(file_path)
        elif file_path.suffix in [".xlsx", ".xls"]:
            df = pd.read_excel(file_path)
        else:
            return None, {}
    except Exception:
        return None, {}

    profile = {
        "columns": list(df.columns),
        "dtypes": {str(k): str(v) for k, v in df.dtypes.items()},
        "shape": df.shape,
        "null_counts": df.isnull().sum().to_dict(),
        "numeric_stats": df.describe().to_dict() if len(df.select_dtypes(include="number").columns) > 0 else {},
    }

    return df, profile
