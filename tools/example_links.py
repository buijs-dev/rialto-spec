#!/usr/bin/env python3
"""Writes the `Examples:` line under every requirement group of the specification.

The line links the Shipment scenarios that list a requirement of the group
(examples/shipment/README.md), the compatibility pairs (examples/compat/README.md) and the test contracts whose diagnostic code
(spec/contract.md) or listed group (VALID below) belongs to it.
Run it after adding a scenario or test contract: python3 tools/example_links.py

The specification is built in slices: the Shipment example, the compatibility pairs and the profiles may not be there
yet. The script reads what exists; a group without any example yet gets PENDING, while the Shipment example is missing.
"""
import re
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parent.parent
REQ=r"[ACKDELMPQRSUV]\d+\.\d+"
group=lambda r: r.split('.')[0]
scen=defaultdict(set)   # group -> scenario ids
SHIPMENT=ROOT/'examples/shipment/README.md'
for line in (SHIPMENT.read_text().splitlines() if SHIPMENT.exists() else []):
    m=re.match(r"\| (S\d\d) ", line)
    if m:
        for r in re.findall(REQ, line): scen[group(r)].add(m.group(1))
# diagnostic code -> requirements
codes={}
for line in (ROOT/'spec/contract.md').read_text().splitlines():
    m=re.match(r"\| `(RIALTO-\w+)` \|.*\| ([^|]+) \|$", line)
    if m: codes[m.group(1)]=re.findall(REQ, m.group(2))
fix=defaultdict(set)
inv=ROOT/'examples/contracts/invalid'
for f in sorted(list(inv.glob('*.yaml'))+list(inv.glob('*/contract.rialto.yaml'))):
    m=re.match(r"# expect: (\S+)", f.read_text())
    if not m: continue  # check_spec reports a test contract without '# expect:'
    rel=f.relative_to(ROOT/'examples/contracts').as_posix()
    if f.name=='contract.rialto.yaml': rel=f.parent.relative_to(ROOT/'examples/contracts').as_posix()+'/'
    for r in codes.get(m.group(1),[]): fix[group(r)].add(rel)
VALID={'valid/errors-identify-type.yaml':['E2'],'valid/fragments/':['K5'],'valid/fragments-recursive/':['K5'],'valid/list.yaml':['Q1'],'valid/link.yaml':['P4'],
        'valid/local-storage.yaml':['K1'],'valid/domain.yaml':['D2','D3'],'valid/minimal.yaml':['K1'],
        'valid/path-location.yaml':['E1','E3'],
        'valid/scope.yaml':['P6'],
        'valid/property-rules.yaml':['D3'],'valid/mapping-paths.yaml':['M2','M3'],
        'valid/storage-joins.yaml':['P2'],'valid/actor-via.yaml':['S4'],
        'valid/presentation.yaml':['U2','U3','U5','U6'],
        # The level contracts (spec/generators.md#conformance-levels): one small application per level.
        'valid/starter.yaml':['D2','D4','M1','M2','R1','R4','E1','E2'],
        'valid/backend.yaml':['P2','P3','P5','P6','Q2','Q3','Q4','L3','S3','A1','A2'],
        'valid/client.yaml':['S2','S5','U2','U3','U5','U6','E4']}
for rel,gs in VALID.items():
    if not (ROOT/'examples/contracts'/rel).exists(): continue
    for g in gs: fix[g].add(rel)
# Compatibility pairs (examples/compat) -> groups, from the requirements their README row lists.
compat=defaultdict(set)
COMPAT=ROOT/'examples/compat/README.md'
for line in (COMPAT.read_text().splitlines() if COMPAT.exists() else []):
    m=re.match(r"\| \[`([\w-]+)`\]", line)
    if m:
        for r in re.findall(REQ, line): compat[group(r)].add(m.group(1))
# Groups that need no example: requirements on the specification itself, not on a contract or a generator.
EXEMPT={'C7':'none: these requirements apply to the specification itself'}
# Groups whose examples are tools rather than contracts; links are relative to the repository root.
TOOLS={'C9':'the sample generator [`tools/sample_generator.py`]({up}tools/sample_generator.py), checked with [`tools/protocol_check.py`]({up}tools/protocol_check.py)'}
# Groups that have no example while the Shipment example, their main source, is not there yet.
PENDING='none yet: the scenarios of the Shipment example follow in a later slice'
docs={'C':ROOT/'spec/core.md','K':ROOT/'spec/contract.md'}
for p in (ROOT/'spec/profiles').glob('*.md'):
    t=p.read_text(); m=re.search(r"prefix (\w) ", t); docs[m.group(1)]=str(p)
stats=0
for prefix,doc in docs.items():
    p=Path(doc); p = p if p.is_absolute() else ROOT/p; t=p.read_text()
    t=re.sub(r"\n\nExamples: [^\n]*", "", t)  # idempotent
    def add(m):
        global stats
        g=m.group(2); parts=[]
        rel_ex=Path('examples/shipment/README.md'); 
        up='../' * (len(p.parent.relative_to(ROOT).parts))
        if scen.get(g):
            ids=', '.join(sorted(scen[g]))
            parts.append(f"scenarios {ids} of the [Shipment example]({up}examples/shipment/README.md#6-scenarios)")
        if fix.get(g):
            links=', '.join(f"[`{r}`]({up}examples/contracts/{r})" for r in sorted(fix[g]))
            parts.append(f"test contracts {links}")
        if compat.get(g):
            links=', '.join(f"[`{r}`]({up}examples/compat/{r}/)" for r in sorted(compat[g]))
            parts.append(f"compatibility pairs {links}")
        if g in EXEMPT: parts=[EXEMPT[g]]
        if g in TOOLS: parts.append(TOOLS[g].format(up=up))
        if not parts and not SHIPMENT.exists(): parts=[PENDING]
        if not parts: return m.group(0)
        stats+=1
        return m.group(0)+"\n\nExamples: "+"; ".join(parts)+"."
    t=re.sub(r"^(### |## )("+prefix+r"\d+)\. [^\n]+", add, t, flags=re.M)
    p.write_text(t)
print("groups with examples:", stats)
