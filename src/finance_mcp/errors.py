"""Custom exceptions used across the finance_mcp package."""

from __future__ import annotations


class FinanceMCPError(Exception):
    """Base class for all finance_mcp exceptions."""


class ParseError(FinanceMCPError):
    """Raised when a bank CSV cannot be parsed."""


class DuplicateTransactionError(FinanceMCPError):
    """Raised when a transaction with the same dedup hash already exists."""


class RuleConflictError(FinanceMCPError):
    """Raised when a categorization rule conflicts with an existing rule."""


class CategoryNotFoundError(FinanceMCPError):
    """Raised when a category lookup by name or id fails."""


class AccountNotFoundError(FinanceMCPError):
    """Raised when an account lookup by name or id fails."""
