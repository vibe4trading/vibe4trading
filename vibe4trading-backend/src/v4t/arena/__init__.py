"""Strategy Arena / tournament execution.

MVP note: this module is intentionally small and DB-backed (no MQ split). It creates
submissions that expand into multiple replay runs across fixed scenario windows.
"""
