"""Platform-protection governance checks."""

from lab.governance.checks.platform import (
    BaselineManifestCheck,
    CompletionCommandsCheck,
    ProtectedPathsCheck,
)

__all__ = ["BaselineManifestCheck", "CompletionCommandsCheck", "ProtectedPathsCheck"]
