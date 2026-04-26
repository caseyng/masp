from __future__ import annotations
from models import RegistryKeyError


class Registry:
    def __init__(self, mapping: dict) -> None:
        seen_names: set[str] = set()
        for task_type, agent_class in mapping.items():
            name = getattr(agent_class, "name", None)
            if name and name in seen_names:
                raise RuntimeError(f"Duplicate agent name: {name!r}")
            if name:
                seen_names.add(name)
        self._mapping: dict = dict(mapping)

    def get(self, task_type: str):
        if task_type not in self._mapping:
            raise RegistryKeyError(f"Unknown task_type: {task_type!r}")
        return self._mapping[task_type]

    def keys(self) -> set[str]:
        return set(self._mapping.keys())

    def __repr__(self) -> str:
        return f"Registry(task_types={list(self._mapping.keys())})"


def build_registry() -> Registry:
    from agents.injection import InjectionCheckAgent
    from agents.auth import AuthCheckAgent
    from agents.xss import XSSCheckAgent
    from agents.generic import GenericAuditAgent

    # Priority order: specific types first, generic_audit MUST be last.
    return Registry({
        "injection_check": InjectionCheckAgent,
        "auth_check":      AuthCheckAgent,
        "xss_check":       XSSCheckAgent,
        "generic_audit":   GenericAuditAgent,
    })
