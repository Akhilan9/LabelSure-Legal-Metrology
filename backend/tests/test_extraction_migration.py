from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from app.db.session import build_engine
from app.core.config import Settings

def test_phase5_upgrade_preserves_evidence(tmp_path, monkeypatch):
    url = "sqlite:///" + (tmp_path / "migration.db").as_posix()
    monkeypatch.setenv("LABELSURE_DATABASE_URL", url)
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "0004_ocr")
    engine = build_engine(url)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO users (id,email,full_name,hashed_password,role,is_active,created_at,updated_at) VALUES ('u','u@example.test','User','hash','INSPECTOR',1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
        conn.execute(text("INSERT INTO inspections (id,inspection_code,created_by_user_id,status,created_at,updated_at) VALUES ('i','INS-2026-000001','u','DRAFT',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
        conn.execute(text("INSERT INTO inspection_images (id,inspection_id,uploaded_by_user_id,original_filename,stored_filename,storage_path,mime_type,file_size,sha256,panel_type,upload_order,created_at) VALUES ('im','i','u','e.jpg','e.jpg','e.jpg','image/jpeg',1,'abc','FRONT',0,CURRENT_TIMESTAMP)"))
        conn.execute(text("INSERT INTO ocr_runs (id,inspection_id,inspection_image_id,engine_name,engine_version,language_config,status,block_count,started_at,ocr_version,created_at,updated_at) VALUES ('r','i','im','MockOCR','1','en','SUCCESS',1,CURRENT_TIMESTAMP,'1',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
        conn.execute(text("""INSERT INTO ocr_blocks (id,ocr_run_id,inspection_id,inspection_image_id,block_index,raw_text,normalized_text,confidence,confidence_tier,polygon,bounding_box,created_at)
            VALUES ('b','r','i','im',0,'MRP 120','MRP 120',0.99,'GOOD','[]','{}',CURRENT_TIMESTAMP)"""))
    command.upgrade(config, "head")
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT version_num FROM alembic_version")) is not None
        assert conn.scalar(text("SELECT raw_text FROM ocr_blocks WHERE id='b'")) == "MRP 120"
        assert conn.scalar(text("SELECT sha256 FROM inspection_images WHERE id='im'")) == "abc"
    assert {"extraction_runs","declaration_candidates","declaration_candidate_sources"} <= set(inspect(engine).get_table_names())
    command.check(config)
    command.downgrade(config, "0004_ocr")
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT raw_text FROM ocr_blocks WHERE id='b'")) == "MRP 120"
    command.upgrade(config, "head")
    engine.dispose()

