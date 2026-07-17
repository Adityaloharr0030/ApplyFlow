"""
pipeline/__init__.py
────────────────────
The ApplyFlow pipeline exposes four independent, testable stages:

    from pipeline.discover import run_discover
    from pipeline.score    import run_score
    from pipeline.apply    import run_apply
    from pipeline.notify   import run_notify, fire_instant

Each stage has a single responsibility and can be run/tested in isolation.
"""

from pipeline.discover import run_discover
from pipeline.score    import run_score
from pipeline.apply    import run_apply
from pipeline.notify   import run_notify, fire_instant

__all__ = ["run_discover", "run_score", "run_apply", "run_notify", "fire_instant"]
