"""Connector Service Events (NATS audit subjects).

All audit events for the connector_service are published under the
``connector_service.connector.*`` subject family. The events module is
intentionally thin — subject strings are inlined at call sites in
``main.py`` and ``routes_custom.py`` so they stay grep-able.
"""
