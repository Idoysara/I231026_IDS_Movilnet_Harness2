"""
# tests/test_n8n_webhook_resolver.py
# Pruebas unitarias de resolución canónica de webhook n8n
"""

try:
    import pytest
except ImportError:
    pytest = None
from core.n8n_webhook_resolver import (
    resolve_n8n_webhook_url,
    CANONICAL_WEBHOOK_URL,
    CANONICAL_WORKFLOW_ID,
)


def test_resolve_empty_url():
    cfg = resolve_n8n_webhook_url("")
    assert cfg.resolved_url == CANONICAL_WEBHOOK_URL
    assert cfg.was_upgraded is True
    assert cfg.target_workflow_id == CANONICAL_WORKFLOW_ID


def test_resolve_legacy_messages_upsert():
    legacy = "https://n8n.lpgtec.net/webhook/messages_upsert"
    cfg = resolve_n8n_webhook_url(legacy)
    assert cfg.resolved_url == CANONICAL_WEBHOOK_URL
    assert cfg.was_upgraded is True


def test_resolve_already_canonical():
    cfg = resolve_n8n_webhook_url(CANONICAL_WEBHOOK_URL)
    assert cfg.resolved_url == CANONICAL_WEBHOOK_URL
    assert cfg.was_upgraded is False


def test_resolve_external_url():
    ext = "https://my-custom-n8n.io/webhook/custom"
    cfg = resolve_n8n_webhook_url(ext)
    assert cfg.resolved_url == ext
    assert cfg.was_upgraded is False


def test_resolve_invalid_n8n_subpath():
    invalid = "https://n8n.lpgtec.net/webhook/viki-chat"
    cfg = resolve_n8n_webhook_url(invalid)
    assert cfg.resolved_url == CANONICAL_WEBHOOK_URL
    assert cfg.was_upgraded is True

