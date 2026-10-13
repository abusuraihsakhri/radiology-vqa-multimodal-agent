"""
Command Line Interface for Radiology Vqa Multimodal Agent.
"""
import argparse
import csv
import json
import sys
from agents.models import SystemTaskPayload
from agents.supervisor import SystemSupervisor
from agents.base import AuditLogger, SecurityException

supervisor = SystemSupervisor(model_provider="mock")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="radiology-vqa-multimodal-agent", description="Radiology Vqa Multimodal Agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Audit
    p_audit = subparsers.add_parser("audit", help="Run single task evaluation")
    p_audit.add_argument("--task-id", default="TASK-2026-001")
    p_audit.add_argument("--target", default="KEY-TARGET-01")
    p_audit.add_argument("--primary", type=float, default=28.5)
    p_audit.add_argument("--secondary", type=float, default=14.2)
    p_audit.add_argument("--critical", action="store_true")
    p_audit.add_argument("--status", default="DISCORDANT")

    # Chat
    p_chat = subparsers.add_parser("chat", help="System configuration query")
    p_chat.add_argument("query", nargs="+")

    # Batch
    p_batch = subparsers.add_parser("batch", help="Batch process CSV records")
    p_batch.add_argument("-i", "--input", required=True)
    p_batch.add_argument("-o", "--output", default="results.csv")

    # Verify Audit
    subparsers.add_parser("verify-audit", help="Verify HMAC audit trail integrity")

    # Serve
    p_serve = subparsers.add_parser("serve", help="Launch FastAPI REST server")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)

    args = parser.parse_args(argv)

    if args.command == "audit":
        payload = SystemTaskPayload(
            task_id=args.task_id,
            target_identifier=args.target,
            primary_metric=args.primary,
            secondary_metric=args.secondary,
            status_descriptor=args.status,
            is_critical_flag=args.critical,
        )
        dossier = supervisor.process_task(payload)
        print("=" * 80)
        print(f"  RADIOLOGY VQA MULTIMODAL AGENT")
        print(f"  Domain: Synthetic rule evaluation | Standard: Illustrative thresholds only")
        print(f"  Dossier ID: {dossier.dossier_id} | Urgency: [{dossier.overall_urgency.value}]")
        print("=" * 80)
        for a in dossier.alerts:
            print(f"\n  [{a.urgency.value}] from {a.origin_worker}:")
            print(f"  Summary: {a.summary}")
            print(f"  Details: {a.technical_details}")
            print(f"  Action:  {a.actionable_remediation}")
        print(f"\n  HMAC-SHA256 Audit Hash: {dossier.audit_hash}")
        print("=" * 80)
        return 0

    if args.command == "chat":
        ans = supervisor.query_supervisory_chat(" ".join(args.query))
        print(f"\n[Radiology Vqa Multimodal Agent Supervisor]:\n{ans}\n")
        return 0

    if args.command == "verify-audit":
        trail = AuditLogger.get_trail()
        valid = AuditLogger.verify_integrity()
        print(f"Audit Trail Blocks: {len(trail)} | Cryptographic Integrity Verified: {valid}")
        return 0 if valid else 1

    if args.command == "batch":
        try:
            with open(args.input, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                fieldnames = list(reader.fieldnames or [])
                rows = list(reader)
        except FileNotFoundError:
            print(f"Error: Input file '{args.input}' not found.", file=sys.stderr)
            return 1
        except PermissionError:
            print(f"Error: Permission denied reading '{args.input}'.", file=sys.stderr)
            return 1
        except (csv.Error, UnicodeError, IsADirectoryError) as e:
            print(f"Error: Malformed CSV in '{args.input}': {e}", file=sys.stderr)
            return 1

        if not fieldnames or any(not key for key in fieldnames):
            print("Error: CSV must have nonempty column headers.", file=sys.stderr)
            return 1
        required = {"task_id", "target_identifier", "primary_metric"}
        if not required.issubset(fieldnames):
            print(f"Error: Missing required CSV columns: {', '.join(sorted(required - set(fieldnames)))}.", file=sys.stderr)
            return 1
        out_fields = list(dict.fromkeys(fieldnames + ["overall_urgency", "integrity_status", "total_alerts", "audit_hash"]))
        out_rows = []
        errors = 0
        for idx, r in enumerate(rows):
            try:
                if None in r:
                    raise ValueError("Too many columns in CSV row")
                critical_value = str(r.get("is_critical_flag", "")).strip().lower()
                if critical_value not in ("true", "false", "1", "0", "yes", "no", ""):
                    raise ValueError("Invalid is_critical_flag; expected true/false, 1/0, or yes/no")
                payload = SystemTaskPayload(
                    task_id=r.get("task_id", "TASK-01"),
                    target_identifier=r.get("target_identifier", "TARGET-01"),
                    primary_metric=float(r.get("primary_metric", 15.0)),
                    secondary_metric=float(r.get("secondary_metric", 5.0)),
                    status_descriptor=r.get("status_descriptor", "NOMINAL"),
                    is_critical_flag=critical_value in ("true", "1", "yes"),
                )
                dossier = supervisor.process_task(payload)
                row_dict = dict(r)
                row_dict["overall_urgency"] = dossier.overall_urgency.value
                row_dict["integrity_status"] = dossier.integrity_status.value
                row_dict["total_alerts"] = dossier.total_alerts
                row_dict["audit_hash"] = dossier.audit_hash
                out_rows.append(row_dict)
            except (ValueError, TypeError, SecurityException) as e:
                print(f"Warning: Skipping row {idx + 1}: {e}", file=sys.stderr)
                errors += 1

        try:
            with open(args.output, mode="w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=out_fields)
                writer.writeheader()
                writer.writerows(out_rows)
        except (PermissionError, IsADirectoryError, OSError) as e:
            print(f"Error: Could not write '{args.output}': {e}", file=sys.stderr)
            return 1

        print(f"Processed {len(out_rows)} records -> {args.output} ({errors} skipped)")
        return 0

    if args.command == "serve":
        import uvicorn
        from agents.api import app
        print(f"Starting Radiology Vqa Multimodal Agent API server on http://{args.host}:{args.port}")
        uvicorn.run(app, host=args.host, port=args.port)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
