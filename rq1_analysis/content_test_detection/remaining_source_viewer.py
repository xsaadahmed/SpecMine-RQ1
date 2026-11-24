"""Build an offline viewer from the versioned unresolved-PR audit."""

from collections import Counter
from html import escape
import json

import pandas as pd

from ai_assisted import DEST, full_cohort
from common import KEY, file_hash
from detector import eligible, priority
from storage import Store, metadata_request


REPORT = DEST / 'codex_source_review_v16'
OUTPUT = REPORT / 'source_review.html'


def source_section(store, repo, sha, file, blocker, in_study):
    path = file['filename']
    text, provenance, _ = store.content(repo, sha, path, file.get('sha'))
    status = provenance['status']
    note = ''
    if not in_study:
        note += '<p class="notice">This addition is outside the frozen file list.</p>'
    if blocker:
        flags = [blocker[key] for key in ('retrieval', 'model_status', 'diagnostic') if blocker.get(key)]
        note += f'<p>Audit notes · {escape(" · ".join(flags))}</p>'
    heading = escape(path)
    if text is None:
        body = f'<p>Pinned source unavailable · {escape(status)}</p>'
    else:
        lines = '\n'.join(f'{i:5}  {line}' for i, line in enumerate(text.splitlines(), 1))
        identity = f"Git blob {provenance['blob_sha']} · SHA-256 {provenance['content_sha256']}"
        body = f'<p class="identity">{escape(identity)}</p><pre>{escape(lines)}</pre>'
    return f'<details class="file"><summary>{heading}</summary>{note}{body}</details>\n', status


def build():
    audit = pd.read_csv(REPORT / 'all_85_review.csv').query("outcome == 'unknown'")
    assert len(audit) == 72 and not audit.duplicated(KEY).any()
    groups = full_cohort.groups()
    store = Store()
    entries = []
    counts = Counter()
    for index, row in enumerate(audit.itertuples(index=False), 1):
        repo, number = row.repo_name, int(row.pr_number)
        ident = f'pr-{index:02}'
        title = escape(f'{repo} #{number}')
        entries.append(f'<li><a href="#{ident}">{title}</a></li>')
    with OUTPUT.with_suffix('.tmp').open('w', encoding='utf-8', newline='\n') as out:
        out.write("""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>SpecMine RQ1 remaining source review</title>
<style>
body{max-width:1120px;margin:2rem auto;padding:0 1rem;font:1rem system-ui;color:#172235}
article,details{border:1px solid #c0cada;border-radius:.45rem;padding:.85rem;margin:1rem 0}
article:target{border:2px solid #315e9c} summary{cursor:pointer;font-weight:650;overflow-wrap:anywhere}
pre{overflow:auto;max-height:70vh;background:#f2f5f9;padding:1rem;tab-size:4}
.identity{font:.85rem monospace;overflow-wrap:anywhere}
.notice{background:#fff4d5;padding:.6rem}nav ul{columns:2;padding-left:1.4rem}
@media(max-width:680px){nav ul{columns:1}}
</style></head><body>
<h1>SpecMine RQ1 remaining source review</h1>
<p>All 72 unknown PRs from the latest offline pass. Each entry includes the audit explanation and any locally available, hash-verified added source eligible under the study rules. Expand a file to see its complete source with line numbers.</p>
<nav id="index" aria-label="PR index"><h2>PR index</h2><ul>""")
        out.write('\n'.join(entries) + '</ul></nav>\n')
        for index, row in enumerate(audit.itertuples(index=False), 1):
            repo, number = row.repo_name, int(row.pr_number)
            frozen = {(r.file_path, r.change_status) for r in groups[repo, number].itertuples()}
            frozen_added = {path for path, status in frozen if status == 'added' and eligible(path)}
            meta = store.data(metadata_request(repo, number))
            files, complete, _, why = store.files(repo, number)
            observed = {(file['filename'], file['status']) for file in files or []}
            added = sorted((file for file in files or [] if file['status'] == 'added' and eligible(file['filename'])),
                           key=lambda file: (priority(file['filename']), file['filename']))
            focus = {item['path']: item for item in json.loads(row.diagnostic_details) if isinstance(item, dict)}
            out.write(f'<article id="pr-{index:02}"><h2>{escape(repo)} #{number}</h2>'
                      f'<p><strong>Why unknown</strong> — {escape(row.explanation.replace(chr(96), ""))}</p>')
            if meta:
                out.write(f'<p class="identity">Cached PR head · {escape(meta["head_sha"])}</p>')
            if complete and observed != frozen:
                out.write('<p class="notice">The cached diff differs from the frozen study. '
                          'Source shown here documents the cached head only.</p>')
            elif not complete:
                out.write(f'<p class="notice">Pinned file list unavailable or incomplete · {escape(why)}</p>')
            missing = sorted(frozen_added - {file['filename'] for file in added})
            if missing:
                out.write('<details><summary>Frozen eligible additions absent from the cached diff '
                          f'({len(missing)})</summary><ul>')
                out.write(''.join(f'<li>{escape(path)}</li>' for path in missing) + '</ul></details>')
            out.write(f'<details open><summary>Cached eligible added paths ({len(added)})</summary>\n')
            if not added:
                out.write('<p>No eligible added file is available from the cached file list.</p>')
            for file in added:
                section, status = source_section(store, repo, meta['head_sha'], file,
                                                 focus.get(file['filename']), file['filename'] in frozen_added)
                out.write(section)
                counts[status] += 1
            out.write('</details><p><a href="#index">Back to PR index</a></p></article>\n')
        out.write('</body></html>\n')
    OUTPUT.with_suffix('.tmp').replace(OUTPUT)
    print(json.dumps({'prs': len(audit), 'file_statuses': counts, 'bytes': OUTPUT.stat().st_size,
                      'sha256': file_hash(OUTPUT)}, indent=2))


if __name__ == '__main__':
    build()
