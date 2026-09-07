import json
from pathlib import Path
from app.rules.schemas import RuleSet

MANIFEST={("labelsure_prototype","1"): "packaged_commodities_prototype_v1.json"}
MANIFEST.update({('LMPC-'+era,'1'): ('lmpc-'+era).lower()+'.json' for era in ['2011-BASE','2017-AMENDMENTS','2021-AMENDMENTS','2026-RULES']})
MAX_RULE_FILE_BYTES=256_000

def reject_duplicates(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise ValueError("Duplicate JSON key")
        result[key]=value
    return result

def parse_ruleset(raw):
    if len(raw)>MAX_RULE_FILE_BYTES: raise ValueError("Rule file too large")
    def invalid_constant(value): raise ValueError("Non-finite rule value")
    data=json.loads(raw,object_pairs_hook=reject_duplicates,parse_constant=invalid_constant)
    return RuleSet.model_validate(data)

def load_ruleset(ruleset_id,version):
    filename=MANIFEST.get((ruleset_id,version))
    if not filename: raise ValueError("Unknown configured ruleset/version")
    path=Path(__file__).parent/"definitions"/filename
    with path.open("rb") as stream: raw=stream.read(MAX_RULE_FILE_BYTES+1)
    ruleset=parse_ruleset(raw)
    if (ruleset.ruleset_id,ruleset.ruleset_version)!=(ruleset_id,version):
        raise ValueError("Ruleset identity mismatch")
    return ruleset

