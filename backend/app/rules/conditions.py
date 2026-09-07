"""A bounded three-valued DSL over an explicit flat key allowlist."""
from app.context.facts import KEYS
ALLOWED_KEYS=set(KEYS.values())|{"evidence.sufficiency"}
SCALAR={"equals","not_equals","in","not_in","exists","not_exists","greater_than","greater_or_equal","less_than","less_or_equal"}
GROUP={"all","any","none"}

def validate_condition(node,depth=0,budget=None):
    budget=budget if budget is not None else [0]
    budget[0]+=1
    if depth>8 or budget[0]>100 or not isinstance(node,dict):
        raise ValueError("Invalid or oversized condition tree")
    groups=set(node)&GROUP
    if groups:
        if len(node)!=1 or len(groups)!=1:
            raise ValueError("Malformed condition group")
        children=node[next(iter(groups))]
        if not isinstance(children,list) or not 1<=len(children)<=30:
            raise ValueError("Condition groups require 1–30 children")
        for child in children: validate_condition(child,depth+1,budget)
        return
    if set(node)-{"key","operator","value"} or not {"key","operator"}<=set(node):
        raise ValueError("Malformed condition")
    if node["key"] not in ALLOWED_KEYS or node["operator"] not in SCALAR:
        raise ValueError("Unsupported key or operator")
    op=node["operator"]
    if op in {"exists","not_exists"}:
        if "value" in node: raise ValueError("Existence operators take no value")
    elif "value" not in node:
        raise ValueError("Missing condition value")
    elif op in {"in","not_in"}:
        if not isinstance(node["value"],list) or not 1<=len(node["value"])<=30:
            raise ValueError("Membership requires a bounded list")
        if any(not isinstance(x,(str,int,float,bool)) for x in node["value"]):
            raise ValueError("Membership values must be scalar")
    elif not isinstance(node["value"],(str,int,float,bool)):
        raise ValueError("Condition value must be scalar")
    if op in {"greater_than","greater_or_equal","less_than","less_or_equal"} and type(node["value"]) not in {int,float}:
        raise ValueError("Numeric comparison requires a number")

def condition(node,keys):
    if "all" in node or "any" in node or "none" in node:
        op=next(iter(node))
        values=[condition(n,keys) for n in node[op]]
        if op=="all":
            return False if False in values else None if None in values else True
        any_value=True if True in values else None if None in values else False
        return (not any_value) if op=="none" and any_value is not None else any_value
    item=keys.get(node["key"])
    if not item or item.get("state")!="KNOWN":
        return None
    value=item.get("value")
    if value is None:
        return False if node["operator"]=="exists" else True if node["operator"]=="not_exists" else None
    if value=="UNKNOWN":
        return None
    op=node["operator"]
    target=node.get("value")
    if op=="exists": return True
    if op=="not_exists": return False
    if op=="equals": return type(value)==type(target) and value==target
    if op=="not_equals": return not (type(value)==type(target) and value==target)
    if op=="in": return any(type(value)==type(t) and value==t for t in target)
    if op=="not_in": return not any(type(value)==type(t) and value==t for t in target)
    if type(value) not in {int,float}: return None
    if op=="greater_than": return value>target
    if op=="greater_or_equal": return value>=target
    if op=="less_than": return value<target
    if op=="less_or_equal": return value<=target
    return None

def referenced_keys(node):
    if "key" in node: return {node["key"]}
    return set().union(*(referenced_keys(c) for children in node.values() for c in children))

