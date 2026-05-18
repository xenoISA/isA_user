"""Factory helpers for developer_service."""

from .developer_service import DeveloperOverviewService


def create_developer_service() -> DeveloperOverviewService:
    return DeveloperOverviewService()
