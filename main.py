#!/usr/bin/env python3
import json
import sys

from auditor import Auditor
from configurator import Configurator
from decomposer import Decomposer
from llm_provider import build_llm_provider
from models import PipelineError, ConfigurationError
from orchestrator import Orchestrator
from registry import build_registry


def _print_report(report) -> None:
    print(json.dumps({
        "run_id":               report.run_id,
        "sufficient":           report.sufficient,
        "successful_count":     report.successful_count,
        "failed_count":         report.failed_count,
        "sufficiency_threshold": report.sufficiency_threshold,
        "results": [
            {
                "task_type":    r.task_type,
                "success":      r.success,
                **({"content":      r.content}      if r.success  else {}),
                **({"failure_mode": r.failure_mode} if not r.success else {}),
                **({"reason":       r.reason}       if r.reason   else {}),
            }
            for r in report.results
        ],
    }, indent=2, ensure_ascii=False))


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: main.py <audit_request>", file=sys.stderr)
        return 1

    audit_request = sys.argv[1]

    try:
        config = Configurator().build()
    except ConfigurationError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1

    llm_provider = build_llm_provider(config.llm_base_url, config.llm_model, config.llm_api_key)
    registry     = build_registry()

    try:
        auditor = Auditor(config.audit_log_path)
    except ConfigurationError as e:
        print(f"Audit log error: {e}", file=sys.stderr)
        return 1

    decomposer   = Decomposer(llm_provider, config.decomposer_temperature)
    orchestrator = Orchestrator(config, registry, decomposer, auditor, llm_provider)

    try:
        report = orchestrator.run(audit_request)
        _print_report(report)
        return 0
    except PipelineError as e:
        print(f"Pipeline error: {e.failure_mode}", file=sys.stderr)
        if e.reason:
            print(f"  reason: {e.reason}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        orchestrator.close()


if __name__ == "__main__":
    sys.exit(main())
