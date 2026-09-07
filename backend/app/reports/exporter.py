import csv
import io
import json
from hashlib import sha256
from typing import Any


DANGEROUS_CSV_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "%")


def sanitize_csv_cell(value: Any) -> str:
    """
    Guards against CSV Formula / DDE Injection attacks.
    Prepends dangerous leading characters with a single apostrophe.
    """
    if value is None:
        return ""
    text = str(value)
    if text and text.startswith(DANGEROUS_CSV_PREFIXES):
        return "'" + text
    return text


def generate_rules_csv(report_data: dict) -> str:
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Header section
    writer.writerow(["# LabelSure Legal Metrology Compliance Inspection Violation & Rule Export"])
    writer.writerow(["# Inspection Code", sanitize_csv_cell(report_data.get("inspection_code"))])
    writer.writerow(["# Overall Status", sanitize_csv_cell(report_data.get("overall_compliance"))])
    writer.writerow(["# Generated At", sanitize_csv_cell(report_data.get("generated_at"))])
    writer.writerow(["# Verification Checksum", sanitize_csv_cell(report_data.get("tamper_sha256"))])
    writer.writerow([])

    # Table columns
    writer.writerow([
        "Rule Key",
        "Title",
        "Machine Verdict",
        "Inspector Final Verdict",
        "Is Overridden",
        "Override Reason",
        "Legal Reference",
        "Severity",
        "Legal Status"
    ])

    for r in report_data.get("rule_evaluations", []):
        writer.writerow([
            sanitize_csv_cell(r.get("rule_key")),
            sanitize_csv_cell(r.get("title")),
            sanitize_csv_cell(r.get("original_verdict") or r.get("machine_verdict")),
            sanitize_csv_cell(r.get("final_verdict")),
            sanitize_csv_cell(r.get("is_overridden")),
            sanitize_csv_cell(r.get("override_reason")),
            sanitize_csv_cell(r.get("legal_reference")),
            sanitize_csv_cell(r.get("severity")),
            sanitize_csv_cell(r.get("legal_status")),
        ])

    return output.getvalue()


def generate_declarations_csv(report_data: dict) -> str:
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    writer.writerow(["# LabelSure Declaration Candidates & Evidence Ledger"])
    writer.writerow(["# Inspection Code", sanitize_csv_cell(report_data.get("inspection_code"))])
    writer.writerow([])

    writer.writerow([
        "Candidate ID",
        "Declaration Type",
        "Normalized Value",
        "Raw Value",
        "Confidence Score",
        "Extraction Method",
        "Needs Review",
        "Review Status"
    ])

    for d in report_data.get("declarations_summary", []):
        writer.writerow([
            sanitize_csv_cell(d.get("id")),
            sanitize_csv_cell(d.get("declaration_type")),
            sanitize_csv_cell(d.get("normalized_value")),
            sanitize_csv_cell(d.get("raw_value")),
            sanitize_csv_cell(d.get("confidence_score")),
            sanitize_csv_cell(d.get("extraction_method")),
            sanitize_csv_cell(d.get("needs_review")),
            sanitize_csv_cell(d.get("review_status")),
        ])

    return output.getvalue()


def canonical_json_dump(data: dict) -> str:
    return json.dumps(data, sort_keys=True, indent=2, default=str)


def compute_sha256(content: str | bytes) -> str:
    if isinstance(content, str):
        content = content.encode("utf-8")
    return sha256(content).hexdigest()
