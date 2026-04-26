import os

from models import (
    Config,
    AgentConfig,
    InjectionCheckAgentConfig,
    AuthCheckAgentConfig,
    XSSCheckAgentConfig,
    GenericAuditAgentConfig,
    ConfigurationError,
)

_AGENT_CONFIG_CLASSES: dict[str, type[AgentConfig]] = {
    "injection_check": InjectionCheckAgentConfig,
    "auth_check":      AuthCheckAgentConfig,
    "xss_check":       XSSCheckAgentConfig,
    "generic_audit":   GenericAuditAgentConfig,
}

_DEFAULT_MAX_TOKENS = 1024


class Configurator:
    def build(self) -> Config:
        use_mock = os.environ.get("USE_MOCK_LLM", "").strip()

        if use_mock:
            llm_base_url = os.environ.get("LLM_BASE_URL", "http://mock")
            llm_model    = os.environ.get("LLM_MODEL", "mock")
            llm_api_key  = os.environ.get("LLM_API_KEY", "")
        else:
            llm_base_url = self._require("LLM_BASE_URL", "llm_base_url")
            llm_model    = self._require("LLM_MODEL",    "llm_model")
            llm_api_key  = self._optional_str("LLM_API_KEY", "")

        audit_log_path        = self._optional_str("AUDIT_LOG_PATH",        "audit.jsonl")
        sufficiency_threshold = self._optional_int("SUFFICIENCY_THRESHOLD", 1,   "sufficiency_threshold")
        max_workers           = self._optional_int("MAX_WORKERS",           4,   "max_workers")
        decomposer_temperature = self._optional_float("DECOMPOSER_TEMPERATURE", 0.0, "decomposer_temperature")
        agent_temperature     = self._optional_float("AGENT_TEMPERATURE",   0.1, "agent_temperature")

        if sufficiency_threshold < 0:
            raise ConfigurationError("sufficiency_threshold must be >= 0")
        if max_workers < 1:
            raise ConfigurationError("max_workers must be >= 1")
        if not (0.0 <= decomposer_temperature <= 1.0):
            raise ConfigurationError("decomposer_temperature must be in [0.0, 1.0]")
        if not (0.0 <= agent_temperature <= 1.0):
            raise ConfigurationError("agent_temperature must be in [0.0, 1.0]")

        agent_configs: dict[str, AgentConfig] = {}
        for task_type, config_class in _AGENT_CONFIG_CLASSES.items():
            env_prefix = task_type.upper()
            temp   = self._optional_float(f"{env_prefix}_TEMPERATURE", agent_temperature, f"{task_type}.temperature")
            tokens = self._optional_int(f"{env_prefix}_MAX_TOKENS",   _DEFAULT_MAX_TOKENS, f"{task_type}.max_tokens")
            try:
                agent_configs[task_type] = config_class(temperature=temp, max_tokens=tokens)
            except ValueError as e:
                raise ConfigurationError(f"Invalid config for {task_type!r}: {e}") from e

        # Validate keyset against registry
        from registry import build_registry
        registry_keys = build_registry().keys()
        config_keys   = set(agent_configs.keys())
        if config_keys != registry_keys:
            missing = registry_keys - config_keys
            extra   = config_keys - registry_keys
            raise ConfigurationError(
                f"config_agent_keyset_mismatch: missing={missing!r}, extra={extra!r}"
            )

        return Config(
            llm_base_url=llm_base_url,
            llm_model=llm_model,
            llm_api_key=llm_api_key,
            audit_log_path=audit_log_path,
            sufficiency_threshold=sufficiency_threshold,
            max_workers=max_workers,
            decomposer_temperature=decomposer_temperature,
            agent_configs=agent_configs,
        )

    def _require(self, var: str, field: str) -> str:
        val = os.environ.get(var, "").strip()
        if not val:
            raise ConfigurationError(f"Required field {field!r} missing — set env var {var}")
        return val

    def _optional_str(self, var: str, default: str) -> str:
        val = os.environ.get(var, "").strip()
        return val if val else default

    def _optional_int(self, var: str, default: int, field: str) -> int:
        raw = os.environ.get(var, "").strip()
        if not raw:
            return default
        try:
            return int(raw)
        except ValueError:
            raise ConfigurationError(f"Field {field!r}: expected int, got {raw!r}")

    def _optional_float(self, var: str, default: float, field: str) -> float:
        raw = os.environ.get(var, "").strip()
        if not raw:
            return default
        try:
            return float(raw)
        except ValueError:
            raise ConfigurationError(f"Field {field!r}: expected float, got {raw!r}")

    def __repr__(self) -> str:
        return "Configurator()"
