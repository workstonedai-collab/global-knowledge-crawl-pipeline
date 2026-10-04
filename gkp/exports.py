from __future__ import annotations

import csv
import json
import os
import re
import tempfile
import zipfile
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

from .common import get_path, json_text, safe_cell

SYSTEM_COLUMNS = ["_id", "_url", "_status", "_issues", "_published_at", "_collected_at", "_sources"]


def atomic_write(path: Path, writer):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, filename = tempfile.mkstemp(dir=path.parent, prefix=".gkp-", suffix=".tmp")
    os.close(handle)
    temporary = Path(filename)
    try:
        writer(temporary)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_json(path: Path, document):
    atomic_write(path, lambda p: p.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"))


def column_name(index):
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def xlsx_write(path: Path, columns, rows):
    """Minimal standards-based workbook with inline strings and a frozen header."""
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    root = Element("worksheet", xmlns=ns)
    SubElement(root, "dimension", ref="A1:" + column_name(len(columns)) + str(len(rows) + 1))
    views = SubElement(root, "sheetViews")
    view = SubElement(views, "sheetView", workbookViewId="0")
    SubElement(view, "pane", ySplit="1", topLeftCell="A2", activePane="bottomLeft", state="frozen")
    data = SubElement(root, "sheetData")
    for number, values in enumerate([columns] + [[row.get(key) for key in columns] for row in rows], 1):
        row = SubElement(data, "row", r=str(number))
        for index, value in enumerate(values, 1):
            value = safe_cell(value)
            ref = column_name(index) + str(number)
            if type(value) in {float, int}:
                cell = SubElement(row, "c", r=ref)
                SubElement(cell, "v").text = str(value)
            elif isinstance(value, bool):
                cell = SubElement(row, "c", r=ref, t="b")
                SubElement(cell, "v").text = "1" if value else "0"
            else:
                cell = SubElement(row, "c", r=ref, t="inlineStr")
                text = SubElement(SubElement(cell, "is"), "t", {"{http://www.w3.org/XML/1998/namespace}space": "preserve"})
                text.text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(value))[:32767]
    if rows:
        SubElement(root, "autoFilter", ref="A1:" + column_name(len(columns)) + str(len(rows) + 1))
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", '''<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>''')
        archive.writestr("_rels/.rels", '''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>''')
        archive.writestr("xl/workbook.xml", '''<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Information" sheetId="1" r:id="rId1"/></sheets></workbook>''')
        archive.writestr("xl/_rels/workbook.xml.rels", '''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>''')
        archive.writestr("xl/worksheets/sheet1.xml", tostring(root, encoding="utf-8", xml_declaration=True))


def export_records(state, config, directory: Path):
    records = []
    duplicates = []
    table = []
    for row in state.records():
        metadata = json.loads(row["metadata"])
        if row["duplicate_of"]:
            duplicates.append({"id": row["id"], "url": row["url"], "duplicate_of": row["duplicate_of"], "reason": "exact_body", "sources": metadata["sources"]})
            continue
        enriched = state.enriched(row["id"], config.signature)
        result = json.loads(enriched["result"]) if enriched and enriched["result"] else None
        status = result["status"] if result else "failed" if row["fetch_error"] or enriched and enriched["error"] else "pending"
        issues = result["issues"] if result else [code for code in (row["fetch_error"], enriched["error"] if enriched else None) if code]
        record = {"id": row["id"], "metadata": metadata, "body": row["body"], "content_hash": row["body_hash"],
                  "status": status, "issues": issues, "enrichment": result}
        records.append(record)
        fields = result["fields"] if result else {field["name"]: get_path({"metadata": metadata}, field["source"]) for field in config.template["fields"] if field.get("source")}
        table.append({**fields, "_id": row["id"], "_url": row["url"], "_status": status, "_issues": issues,
                      "_published_at": metadata.get("published_at"), "_collected_at": metadata["collected_at"], "_sources": metadata["sources"]})
    columns = [field["name"] for field in config.template["fields"]] + SYSTEM_COLUMNS
    directory.mkdir(parents=True, exist_ok=True)
    if "jsonl" in config.formats:
        atomic_write(directory / "records.jsonl", lambda p: p.write_text("".join(json_text(record) + "\n" for record in records), encoding="utf-8"))
    if "csv" in config.formats:
        def write_csv(path):
            with path.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=columns)
                writer.writeheader()
                writer.writerows({key: safe_cell(value) for key, value in row.items()} for row in table)
        atomic_write(directory / "table.csv", write_csv)
    if "xlsx" in config.formats:
        atomic_write(directory / "table.xlsx", lambda p: xlsx_write(p, columns, table))
    write_json(directory / "review.json", [record for record in records if record["status"] == "needs_review"])
    write_json(directory / "failures.json", [{"id": record["id"], "url": record["metadata"]["url"], "issues": record["issues"]} for record in records if record["status"] == "failed"])
    write_json(directory / "duplicates.json", duplicates)
    changes = state.changes()
    write_json(directory / "changes.json", changes)
    from .preview import evidence_report
    atomic_write(directory / "evidence.html", lambda p: p.write_text(evidence_report(records, changes), encoding="utf-8"))
    return {"records": len(records), "validated": sum(r["status"] == "validated" for r in records),
            "needs_review": sum(r["status"] == "needs_review" for r in records), "failed": sum(r["status"] == "failed" for r in records),
            "pending": sum(r["status"] == "pending" for r in records), "duplicates": len(duplicates)}
