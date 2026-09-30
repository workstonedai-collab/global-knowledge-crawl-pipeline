from __future__ import annotations

import math

from .common import get_path


def json_schema(template):
    properties = {}
    for field in template["fields"]:
        if field.get("source"):
            continue
        entry = {"type": [field["type"], "null"], "description": field.get("instruction", "")}
        if "enum" in field:
            entry["enum"] = field["enum"] + [None]
        if field["type"] == "array":
            entry["items"] = {"type": field.get("items_type", "string")}
        properties[field["name"]] = entry
    return {"type": "object", "properties": {
        "fields": {"type": "object", "properties": properties, "additionalProperties": False},
        "evidence": {"type": "object", "description": "Map each extracted field to a list of exact short source excerpts."}
    }, "required": ["fields", "evidence"], "additionalProperties": False}


def matches_type(value, kind):
    if kind == "integer":
        return type(value) is int
    if kind == "number":
        return type(value) in {int, float} and math.isfinite(value)
    return isinstance(value, {"string": str, "boolean": bool, "array": list, "object": dict}[kind])


def validate_result(response, template, metadata, body):
    issues = []
    fields = {}
    evidence = {}
    if not isinstance(response, dict) or not isinstance(response.get("fields"), dict):
        response = {"fields": {}, "evidence": {}}
        issues.append("invalid_result_structure")
    given = response["fields"]
    quotes = response.get("evidence", {})
    if not isinstance(quotes, dict):
        quotes = {}
        issues.append("invalid_evidence_structure")
    expected = {field["name"] for field in template["fields"] if not field.get("source")}
    for key in sorted(set(given) - expected):
        # Unknown field names are untrusted model text; don't echo them into errors.
        issues.append("unexpected_field")
    for field in template["fields"]:
        name = field["name"]
        source = field.get("source")
        value = get_path({"metadata": metadata}, source) if source else given.get(name)
        valid = True
        if value is not None:
            if not matches_type(value, field["type"]):
                issues.append(name + ":wrong_type")
                valid = False
            elif "enum" in field and value not in field["enum"]:
                issues.append(name + ":outside_enum")
                valid = False
            elif field["type"] == "array" and field.get("items_type") and any(not matches_type(item, field["items_type"]) for item in value):
                issues.append(name + ":wrong_item_type")
                valid = False
        if field.get("required", False) and (value is None or value == "" or value == []):
            issues.append(name + ":required_missing")
        if not source:
            excerpts = quotes.get(name, [])
            if not isinstance(excerpts, list) or any(not isinstance(q, str) or not q.strip() or len(q) > 500 or q not in body for q in excerpts):
                issues.append(name + ":invalid_evidence")
                excerpts = []
            if field.get("evidence_required", False) and value is not None and not excerpts:
                issues.append(name + ":evidence_missing")
            evidence[name] = excerpts
        fields[name] = value if valid else None
    return {"fields": fields, "evidence": evidence, "issues": sorted(set(issues)),
            "status": "needs_review" if issues else "validated"}
