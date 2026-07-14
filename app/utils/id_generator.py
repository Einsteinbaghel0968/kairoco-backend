"""
Sequential ID generation.

IDs are derived from how many data rows already exist in a sheet (i.e. the
next row number), which keeps things simple and requires no separate counter
storage. A process-wide lock serialises "read row count, then append" so two
near-simultaneous submissions handled by different worker threads don't get
the same ID.

Note: this lock is only effective within a single running process. If this
API is ever scaled to multiple processes/machines behind a load balancer,
replace this with an atomic counter (e.g. a dedicated counter cell in the
sheet updated via a batchUpdate, or a small database sequence).
"""

import threading

# One lock per logical sequence (properties vs testimonials) so they don't
# block each other unnecessarily.
_locks: dict[str, threading.Lock] = {}


def get_lock(key: str) -> threading.Lock:
    if key not in _locks:
        _locks[key] = threading.Lock()
    return _locks[key]


def format_property_id(sequence_number: int) -> str:
    """KC-00001, KC-00002, ..."""
    return f"KC-{sequence_number:05d}"
