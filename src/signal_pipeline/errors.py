class PipelineError(Exception):
    """Base class for expected pipeline failures."""


class ConfigError(PipelineError):
    """Configuration is invalid or unsafe."""


class DeliveryError(PipelineError):
    """A destination rejected or did not acknowledge a delivery."""


class StateError(PipelineError):
    """State could not be loaded, validated, or persisted."""
