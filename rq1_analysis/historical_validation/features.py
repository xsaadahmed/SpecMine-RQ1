"""Versioned, structural English feature rules; not the unavailable upstream parser."""
import re

RULE_VERSION = "hv-structural-english-v1"
PATTERNS = {
    "has_acceptance_criteria": re.compile(r"\bacceptance\s+criteri(?:a|on)\b", re.I),
    "has_edge_cases": re.compile(r"\bedge[\s-]+cases?\b", re.I),
}


def structural_features(text):
    from hv_common import FROZEN
    # Keep original line positions, but ignore commented prose and fenced code.
    lines = re.sub(r"<!--.*?-->", lambda m: "\n"*m.group().count("\n"), text, flags=re.S).splitlines()
    headings = []
    fence = None
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        marker = re.match(r"^(`{3,}|~{3,})", stripped)
        if marker:
            char = marker.group()[0]
            if fence is None: fence = char
            elif fence == char: fence = None
            continue
        if fence is not None: continue
        atx = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", stripped)
        bold = re.match(r"^\*\*(.+?)\*\*\s*:?\s*$", stripped)
        setext = number < len(lines) and bool(re.fullmatch(r"\s*(?:={3,}|-{3,})\s*", lines[number]))
        heading = atx.group(1) if atx else bold.group(1) if bold else stripped if setext else None
        if heading:
            headings.append((number, re.sub(r"[*_`]", "", heading)))
    out = {"feature_rule_version": RULE_VERSION, "n_words": len(text.split())}
    for name, pattern in PATTERNS.items():
        evidence = [n for n, value in headings if pattern.search(value)]
        out[name] = int(bool(evidence))
        out[name+"_heading_lines"] = "|".join(map(str,evidence))
    flag, count = FROZEN.testing_requirement(text)
    out["has_testing_requirement"] = flag
    out["testing_directive_lines"] = count
    return out
