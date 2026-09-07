"""Shared library used by the control API, worker, and GPU manager.

The local execution agent deliberately does NOT depend on this package:
it runs on a separately-trusted machine (the laptop) and must remain
independently auditable and independently enforcing of its own policy.
"""
