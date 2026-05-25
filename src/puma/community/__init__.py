"""Public API for the PUMA Community submission flow.

This package exposes the building blocks used to discover shareable runs in
the local PUMA database, construct submission payloads conforming to the v1
schema, validate them, and either save them locally (dry-run) or publish them
as Pull Requests against the public PUMA Community repository at
``github.com/pumacp/puma-community``.

For the CLI entry points (``puma auth``, ``puma share-results``), see the
submodules :mod:`puma.community.auth_cli` and :mod:`puma.community.share_cli`;
those Typer sub-apps are registered directly in :mod:`puma.cli` and are not
re-exported here.

Importing this module has no observable side effects beyond loading the
canonical hardware-profile catalog once (used by the schema's profile_id
validator).
"""

from puma.community.browse_cli import browse
from puma.community.builder import (
    CommunityError,
    ExcludedModelError,
    IncompleteRunError,
    PIIDetectedError,
    RunNotFoundError,
    UnknownScenarioError,
    UnknownStrategyError,
    build_submission_from_run,
)
from puma.community.credentials import (
    SERVICE_TOKEN_PATTERNS,
    SUPPORTED_SERVICES,
    CredentialError,
    CredentialStore,
    InsecurePermissionsError,
    InvalidTokenFormatError,
    mask_token,
)
from puma.community.dry_run_saver import save_dry_run
from puma.community.github_client import (
    APIRateLimitError,
    AuthenticationError,
    CommunityGitHubClient,
    ConflictError,
    GitHubError,
    SubmissionPRResult,
)
from puma.community.integrity import (
    EmptyPredictionsError,
    IntegrityError,
    compute_predictions_hash,
    verify_predictions_hash,
)
from puma.community.pull_cli import pull
from puma.community.ratelimit import LocalRateLimiter
from puma.community.runs_query import (
    ShareableRunSummary,
    get_run_summary,
    list_shareable_runs,
)
from puma.community.schema import (
    HardwareProfile,
    Integrity,
    Metrics,
    RunMetadata,
    Submission,
    Submitter,
    Sustainability,
    validate_no_pii,
)
from puma.community.validate_cli import validate
from puma.community.validator import (
    is_safe_to_publish,
    sweep_pii,
    validate_submission_dict,
    validate_submission_file,
)
from puma.community.verify_cli import verify_hash

SCHEMA_VERSION = "1.0.0"

__all__ = [
    "SCHEMA_VERSION",
    "SERVICE_TOKEN_PATTERNS",
    "SUPPORTED_SERVICES",
    "APIRateLimitError",
    "AuthenticationError",
    "CommunityError",
    "CommunityGitHubClient",
    "ConflictError",
    "CredentialError",
    "CredentialStore",
    "EmptyPredictionsError",
    "ExcludedModelError",
    "GitHubError",
    "HardwareProfile",
    "IncompleteRunError",
    "InsecurePermissionsError",
    "Integrity",
    "IntegrityError",
    "InvalidTokenFormatError",
    "LocalRateLimiter",
    "Metrics",
    "PIIDetectedError",
    "RunMetadata",
    "RunNotFoundError",
    "ShareableRunSummary",
    "Submission",
    "SubmissionPRResult",
    "Submitter",
    "Sustainability",
    "UnknownScenarioError",
    "UnknownStrategyError",
    "browse",
    "build_submission_from_run",
    "compute_predictions_hash",
    "get_run_summary",
    "is_safe_to_publish",
    "list_shareable_runs",
    "mask_token",
    "pull",
    "save_dry_run",
    "sweep_pii",
    "validate",
    "validate_no_pii",
    "validate_submission_dict",
    "validate_submission_file",
    "verify_hash",
    "verify_predictions_hash",
]
