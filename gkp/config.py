from __future__ import annotations

import json
import re
from pathlib import Path

from .common import PipelineError, canonical_url, digest

LIMIT_DEFAULTS = {
    "max_items": 50, "max_search_requests": 10, "max_ai_calls": 20,
    "max_http_requests": 200, "max_total_tokens": 100000,
    "max_output_tokens": 1200, "max_attempts": 3,
}


def read_document(path: Path):
    try:
        raw = path.read_text(encoding="utf-8")
        if path.suffix.lower() in {".yaml", ".yml"}:
            try:
                import yaml
            except ImportError:
                raise PipelineError("yaml_extra_required") from None
            value = yaml.safe_load(raw)
        else:
            value = json.loads(raw)
        return value
    except PipelineError:
        raise
    except Exception:
        raise PipelineError("invalid_config_document") from None


class Config:
    def __init__(self, path: str | Path):
        self.path = Path(path).resolve()
        self.base = self.path.parent
        self.data = read_document(self.path)
        if not isinstance(self.data, dict):
            raise PipelineError("config_must_be_object")
        self.dataset = self.data.get("dataset", "")
        if not isinstance(self.dataset, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", self.dataset):
            raise PipelineError("invalid_dataset_name")
        self.template = read_document(self.resolve(self.data.get("template", "")))
        self._validate_template()
        self.limits = {**LIMIT_DEFAULTS, **self.data.get("limits", {})}
        if any(type(v) is not int or v < 1 for v in self.limits.values()):
            raise PipelineError("limits_must_be_positive_integers")
        if set(self.limits) - set(LIMIT_DEFAULTS):
            raise PipelineError("unknown_limit")
        self.sources = self.data.get("sources", [])
        self.search = self.data.get("search")
        self.fetch = self.data.get("fetch", {})
        self.enrichment = self.data.get("enrichment", {})
        self.offline = self.data.get("offline", False)
        self.formats = self.data.get("output_formats", ["csv", "xlsx", "jsonl"])
        if not isinstance(self.offline, bool) or not isinstance(self.sources, list):
            raise PipelineError("invalid_config_structure")
        if type(self.data.get("allow_private_network", False)) is not bool:
            raise PipelineError("private_network_flag_must_be_boolean")
        overlap = self.data.get("incremental_overlap_hours", 24)
        if type(overlap) not in {int, float} or not 0 <= overlap <= 8760:
            raise PipelineError("invalid_incremental_overlap")
        if not self.formats or not isinstance(self.formats, list) or set(self.formats) - {"csv", "xlsx", "jsonl"}:
            raise PipelineError("invalid_output_formats")
        if not isinstance(self.fetch, dict) or self.fetch.get("provider", "http") not in {"http", "browser"}:
            raise PipelineError("invalid_fetch_provider")
        if type(self.fetch.get("respect_robots", True)) is not bool:
            raise PipelineError("robots_flag_must_be_boolean")
        for key in ("min_text_chars", "max_response_bytes"):
            if key in self.fetch and (type(self.fetch[key]) is not int or self.fetch[key] < 1):
                raise PipelineError("invalid_fetch_size")
        if type(self.fetch.get("timeout_seconds", 20)) not in {int, float} or self.fetch.get("timeout_seconds", 20) <= 0:
            raise PipelineError("invalid_fetch_timeout")
        if not isinstance(self.enrichment, dict) or self.search is not None and not isinstance(self.search, dict):
            raise PipelineError("invalid_service_structure")
        provider = self.enrichment.get("provider")
        if provider not in {"fixture", "chat_completions", "http_json"}:
            raise PipelineError("invalid_enrichment_provider")
        if type(self.enrichment.get("max_text_chars", 12000)) is not int or self.enrichment.get("max_text_chars", 12000) < 1:
            raise PipelineError("invalid_enrichment_text_limit")
        if type(self.enrichment.get("json_mode", True)) is not bool:
            raise PipelineError("json_mode_must_be_boolean")
        if provider == "chat_completions" and not self.enrichment.get("model"):
            raise PipelineError("chat_model_required")
        if provider == "chat_completions" and set(self.enrichment.get("parameters", {})) - {"temperature", "top_p", "seed", "frequency_penalty", "presence_penalty"}:
            raise PipelineError("unsupported_chat_parameter")
        ids = set()
        for source in self.sources:
            if not isinstance(source, dict) or source.get("type") not in {"url", "rss", "listing"}:
                raise PipelineError("invalid_source")
            if not isinstance(source.get("id"), str) or not source["id"] or source["id"] in ids:
                raise PipelineError("source_ids_must_be_unique")
            ids.add(source["id"])
            canonical_url(source.get("url", ""))
            if not isinstance(source.get("keywords", []), list) or any(not isinstance(word, str) for word in source.get("keywords", [])):
                raise PipelineError("invalid_source_keywords")
            if type(source.get("allow_external", False)) is not bool:
                raise PipelineError("external_flag_must_be_boolean")
            if "include_pattern" in source:
                try:
                    re.compile(source["include_pattern"])
                except (re.error, TypeError):
                    raise PipelineError("invalid_listing_pattern") from None
            if self.offline and source["type"] != "url" and not source.get("fixture"):
                raise PipelineError("offline_source_requires_fixture")
        if self.search:
            if self.search.get("provider") not in {"fixture", "http_json"}:
                raise PipelineError("invalid_search_provider")
            if not isinstance(self.search.get("queries"), list) or not all(isinstance(q, str) and q.strip() for q in self.search["queries"]):
                raise PipelineError("invalid_queries")
            if self.offline and self.search["provider"] != "fixture":
                raise PipelineError("offline_search_requires_fixture")
        if self.offline and provider != "fixture":
            raise PipelineError("offline_enrichment_requires_fixture")
        for service in (self.search, self.enrichment):
            if service and service.get("provider") != "fixture":
                canonical_url(service.get("endpoint", ""))
                if service.get("method", "POST").upper() not in {"GET", "POST"}:
                    raise PipelineError("unsupported_http_method")
                headers = service.get("headers", {})
                if not isinstance(headers, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in headers.items()):
                    raise PipelineError("invalid_service_headers")
                if {key.lower() for key in headers} & {"authorization", "x-api-key", service.get("auth_header", "Authorization").lower()}:
                    raise PipelineError("use_credential_env_for_auth")
                env = service.get("credential_env")
                if env is not None and (not isinstance(env, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", env)):
                    raise PipelineError("invalid_credential_env_name")
        # The signature invalidates enrichment when the contract/service changes.
        self.signature = digest({"template": self.template, "enrichment": self.enrichment, "max_output_tokens": self.limits["max_output_tokens"], "engine": "0.1.0"})

    def resolve(self, path: str) -> Path:
        if not isinstance(path, str) or not path:
            raise PipelineError("invalid_file_path")
        return (self.base / path).resolve()

    def _validate_template(self):
        if not isinstance(self.template, dict) or not isinstance(self.template.get("fields"), list) or not self.template["fields"]:
            raise PipelineError("template_requires_fields")
        if not self.template.get("version"):
            raise PipelineError("template_requires_version")
        names = set()
        reserved = {"_id", "_url", "_status", "_issues", "_published_at", "_collected_at", "_sources"}
        for field in self.template["fields"]:
            name = field.get("name") if isinstance(field, dict) else None
            if not isinstance(name, str) or not name.isidentifier() or name.startswith("_") or name in names or name in reserved:
                raise PipelineError("invalid_or_duplicate_field_name")
            names.add(name)
            if field.get("type") not in {"string", "integer", "number", "boolean", "array", "object"}:
                raise PipelineError("invalid_field_type")
            if field.get("items_type", "string") not in {"string", "integer", "number", "boolean", "array", "object"}:
                raise PipelineError("invalid_array_item_type")
            if any(type(field.get(flag, False)) is not bool for flag in ("required", "evidence_required")):
                raise PipelineError("field_flags_must_be_boolean")
            if not field.get("source") and not isinstance(field.get("instruction"), str):
                raise PipelineError("field_requires_source_or_instruction")
            if field.get("source") and field["source"] not in {"metadata.title", "metadata.url", "metadata.published_at", "metadata.source_name", "metadata.snippet"}:
                raise PipelineError("unsupported_metadata_field")
            if "enum" in field and (not isinstance(field["enum"], list) or not field["enum"]):
                raise PipelineError("invalid_field_enum")


class Budget:
    def __init__(self, limits: dict):
        self.limits = limits
        self.counts = {"http_requests": 0, "search_requests": 0, "ai_calls": 0, "tokens_reserved": 0, "tokens_reported": 0}

    def consume(self, counter: str):
        cap = self.limits["max_" + counter]
        if self.counts[counter] >= cap:
            raise self.exceeded(counter)
        self.counts[counter] += 1

    @staticmethod
    def exceeded(counter):
        from .common import BudgetExceeded
        return BudgetExceeded("budget_" + counter)

    def reserve_ai(self, input_estimate: int):
        reserve = input_estimate + self.limits["max_output_tokens"]
        if max(self.counts["tokens_reserved"], self.counts["tokens_reported"]) + reserve > self.limits["max_total_tokens"]:
            raise self.exceeded("total_tokens")
        self.consume("ai_calls")
        self.counts["tokens_reserved"] += reserve
