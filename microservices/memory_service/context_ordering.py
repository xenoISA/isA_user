"""
Context ordering for lost-in-the-middle mitigation.

Implements the serial-position effect strategy (Liu et al., 2023) by placing
highest-importance memories at the start and end of the context, with
lower-importance items in the middle. LLMs attend better to tokens at the
beginning (primacy) and end (recency) of their context window.

Algorithm:
  1. Sort items by importance descending.
  2. Interleave into edge positions: even-indexed items fill from the left,
     odd-indexed items fill from the right.

Result: importance decreases from edges toward the center.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def order_by_importance_edges(
    items: List[Dict[str, Any]],
    importance_key: str = "importance_score",
) -> List[Dict[str, Any]]:
    """
    Place highest-importance items at edges (start/end), lowest in middle.

    Args:
        items: List of memory dicts, each expected to have an importance field.
        importance_key: Dict key used to read the importance score.
            Items missing this key are treated as importance 0.

    Returns:
        A new list with the same items reordered so that the most important
        items occupy the first and last positions, and the least important
        items sit in the middle.
    """
    if len(items) <= 1:
        return list(items)

    sorted_items = sorted(
        items,
        key=lambda x: x.get(importance_key, 0),
        reverse=True,
    )

    result: List[Any] = [None] * len(sorted_items)
    left = 0
    right = len(sorted_items) - 1

    for i, item in enumerate(sorted_items):
        if i % 2 == 0:
            result[left] = item
            left += 1
        else:
            result[right] = item
            right -= 1

    return result
