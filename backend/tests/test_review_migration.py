from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select, text
from app.db.session import build_engine, build_session_factory
from app.models.user import User, Role
from app.models.inspection import Inspection, InspectionImage
from app.models.ocr import OCRRun, OCRBlock, OCRStatus, OCRConfidenceTier
from app.models.extraction import ExtractionRun, DeclarationCandidate, DeclarationCandidateSource
from app.models.context import ContextResolutionRun, InspectionContext, ContextFact, RuleInputSnapshot, ContextRunStatus, ResolutionState
from app.models.rules import RuleEvaluationRun, RuleEvaluationResult, RuleEvaluationEvidence
from datetime import datetime, date


def test_phase8_data_preserved_by_review_migration(tmp_path, monkeypatch):
    url = "sqlite:///" + (tmp_path / "phase8.db").as_posix()
    monkeypatch.setenv("LABELSURE_DATABASE_URL", url)
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "0007_rules")
    engine = build_engine(url)
    with build_session_factory(engine)() as db:
        db.add(User(id="u", email="review_migration@example.test", full_name="Migration", hashed_password="not-a-login", role=Role.INSPECTOR))
        db.flush()
        db.add(Inspection(id="i", inspection_code="INS-2026-000001", created_by_user_id="u"))
        db.flush()
        db.add(InspectionImage(id="im", inspection_id="i", uploaded_by_user_id="u", original_filename="e.png",
            stored_filename="e.png", storage_path="e.png", mime_type="image/png", file_size=1, sha256="a"*64))
        db.flush()
        db.add(OCRRun(id="o", inspection_id="i", inspection_image_id="im", status=OCRStatus.SUCCESS))
        db.flush()
        db.add(OCRBlock(id="b", ocr_run_id="o", inspection_id="i", inspection_image_id="im", block_index=0,
            raw_text="MRP 120", normalized_text="MRP 120", confidence=.99, confidence_tier=OCRConfidenceTier.GOOD, polygon=[], bounding_box={}))
        db.flush()
        db.add(ExtractionRun(id="e", inspection_id="i", version="1", input_fingerprint="f"*64, status="SUCCESS"))
        db.flush()
        candidate = DeclarationCandidate(id="c", extraction_run_id="e", inspection_id="i", declaration_type="MRP",
            raw_value="MRP 120", normalized_value="120.00", source_ocr_run_id="o", source_ocr_block_id="b",
            source_image_id="im", confidence_score=.94, confidence_factors={"ocr":.54},
            extraction_method="KEYWORD_CONTEXT", review_status="AUTO_EXTRACTED")
        candidate.sources = [DeclarationCandidateSource(ocr_block_id="b", sequence_order=0)]
        db.add(candidate)
        db.flush()
        db.add(ContextResolutionRun(id="cr", inspection_id="i", version="1", input_fingerprint="fp"*32, inspector_input={}, status=ContextRunStatus.SUCCESS))
        db.flush()
        db.add(InspectionContext(id="ctx", inspection_id="i", run_id="cr", context_version="1", resolved={}, resolution_status=ResolutionState.KNOWN, evidence={}, conflicts=[]))
        db.flush()
        db.add(RuleInputSnapshot(id="snap", inspection_id="i", run_id="cr", schema_version="1", content={"test": True}, content_sha256="s"*64))
        db.flush()
        run = RuleEvaluationRun(
            id="rr", inspection_id="i", rule_input_snapshot_id="snap", snapshot_sha256="s"*64,
            ruleset_id="ruleset", ruleset_version="1", ruleset_sha256="r"*64, ruleset_definition={},
            engine_version="1.0.0", evaluation_fingerprint="ef"*32, evaluation_date=date(2026, 9, 1),
            status="SUCCESS", overall="PASS", started_at=datetime.now(), completed_at=datetime.now(),
            total_rules=1, pass_count=1, fail_count=0, uncertain_count=0, not_applicable_count=0, skipped_rules=[]
        )
        db.add(run)
        db.commit()

    def rows():
        with engine.connect() as conn:
            return {table: [tuple(r) for r in conn.execute(text('SELECT * FROM "' + table + '" ORDER BY 1'))]
                    for table in ["users", "inspections", "inspection_images", "ocr_runs", "ocr_blocks",
                                  "extraction_runs", "declaration_candidates", "declaration_candidate_sources",
                                  "context_resolution_runs", "inspection_contexts", "rule_input_snapshots",
                                  "rule_evaluation_runs"]}

    before = rows()
    command.upgrade(config, "head")
    assert rows() == before
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT version_num FROM alembic_version")) is not None
    assert {"inspection_reviews", "rule_review_decisions", "declaration_corrections", "ocr_corrections", "audit_events"} <= set(inspect(engine).get_table_names())
    command.check(config)
    command.downgrade(config, "0007_rules")
    assert rows() == before
    command.upgrade(config, "head")
    assert rows() == before
    engine.dispose()
