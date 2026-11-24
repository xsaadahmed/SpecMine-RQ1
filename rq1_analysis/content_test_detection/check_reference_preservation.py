"""Offline, read-only preservation checks for the second reference incident."""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from common import OUT, CACHE, file_hash, protect_prior, write_json
from github_http import read_count


def main():
    directory = OUT / 'full_cohort/incident_integrity_02'
    manifest = json.loads((directory/'preserved.json').read_text())
    def check(item):
        path, expected = item
        p = Path(path)
        return path if not p.is_file() or file_hash(p) != expected else None
    with ThreadPoolExecutor(max_workers=4) as pool:
        changed = [p for p in pool.map(check, manifest.items()) if p is not None]
    frozen = protect_prior()
    ledger = json.loads((OUT/'api_ledger.json').read_text())['attempts']
    result = {'preserved_fingerprints': len(manifest), 'changed': changed,
              'frozen_research_files': frozen, 'github_used': read_count(CACHE),
              'model_attempts': len(ledger),
              'model_reported_cost_usd': sum(a.get('reported_cost_usd', 0) for a in ledger)}
    write_json(directory/'preservation_check.json', result)
    if changed or result['github_used'] != 12085 or len(ledger) != 74:
        raise RuntimeError('Preservation or resource counter changed; inspect report')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
