"""JSON file-based data store for pipeline results.

Provides simple persistence so that:
1. Pipeline results survive across runs
2. The dashboard can read results from analyzers/scorers
3. Historical data accumulates for trend analysis
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Optional

from ttt.models import PipelineContext


DATA_FILENAME = "ttt_data.json"


def save_context(context: PipelineContext) -> str:
    """Save pipeline context to a JSON file in the output directory.

    Args:
        context: The pipeline context to persist.

    Returns:
        Path to the saved JSON file.
    """
    os.makedirs(context.output_dir, exist_ok=True)
    filepath = os.path.join(context.output_dir, DATA_FILENAME)

    data = context.to_dict()
    data["saved_at"] = datetime.now().isoformat()

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    return filepath


def load_context(output_dir: str) -> Optional[PipelineContext]:
    """Load a previously saved pipeline context from disk.

    Args:
        output_dir: Directory containing the ttt_data.json file.

    Returns:
        PipelineContext or None if no saved data exists.
    """
    filepath = os.path.join(output_dir, DATA_FILENAME)

    if not os.path.exists(filepath):
        return None

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return PipelineContext.from_dict(data)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"⚠️  Warning: Could not load data store: {e}")
        return None


def append_to_store(output_dir: str, context: PipelineContext) -> str:
    """Merge new results into an existing data store.

    If a store already exists, new results are appended (not replacing
    existing results from the same tools). This allows accumulation
    of historical data.

    Args:
        output_dir: Directory for the data store.
        context: New context with results to append.

    Returns:
        Path to the updated JSON file.
    """
    existing = load_context(output_dir)

    if existing is not None:
        # Merge: add new results, avoiding duplicates by tool+timestamp
        existing_keys = {
            (r.tool_name, r.timestamp) for r in existing.results
        }
        for result in context.results:
            key = (result.tool_name, result.timestamp)
            if key not in existing_keys:
                existing.results.append(result)

        # Update log files list
        existing.log_files = list(
            set(existing.log_files + context.log_files)
        )
        context = existing

    context.output_dir = output_dir
    return save_context(context)
