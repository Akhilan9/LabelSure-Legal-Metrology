class RuleRegistry:
    def __init__(self,ruleset):
        self.ruleset=ruleset
        self.by_id={r.rule_id:r for r in ruleset.rules}
        self.by_key={r.rule_key:r for r in ruleset.rules}

    def select(self,on_date,allow_prototypes=False):
        active,skipped=[],[]
        for rule in self.ruleset.rules:
            reason=None
            if not rule.enabled or rule.legal_status=="DISABLED": reason="DISABLED"
            # Unverified source profiles produce review findings, never statutory PASS/FAIL.
            elif rule.legal_status=="PROTOTYPE_RULE" and not allow_prototypes: reason="PROTOTYPE_OPT_IN_REQUIRED"
            elif rule.effective_from and on_date<rule.effective_from: reason="OUTSIDE_EFFECTIVE_INTERVAL"
            elif rule.effective_to and on_date>=rule.effective_to: reason="OUTSIDE_EFFECTIVE_INTERVAL"
            if reason: skipped.append({"rule_id":rule.rule_id,"reason":reason})
            else: active.append(rule)
        return active,skipped

