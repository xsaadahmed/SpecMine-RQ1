"""Isolated extension paths and immutable prior-work protection."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
HIST=BASE/'historical_validation'
ROOT=BASE.parent
OUT=HERE/'outputs'
CACHE=HERE/'cache'
for p in [OUT,OUT/'tables',OUT/'figures',OUT/'content',CACHE/'github',CACHE/'deterministic',CACHE/'grok',HERE/'tests']:
    p.mkdir(parents=True,exist_ok=True)
KEY=['repo_name','pr_number']


def sha256(data):return hashlib.sha256(data).hexdigest()


def file_hash(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def write_json(path,obj,immutable=False):
    text=json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False,default=str)
    if immutable and path.exists():
        if json.loads(path.read_text(encoding='utf-8'))!=json.loads(text):raise RuntimeError('Immutable artifact differs: '+path.name)
        return
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(text,encoding='utf-8');tmp.replace(path)


def protect_prior():
    m=json.loads((HERE/'prior_work_manifest.json').read_text())
    for name,expected in m.items():
        p=ROOT/name
        assert p.exists() and p.stat().st_size==expected['bytes'] and file_hash(p)==expected['sha256'],'Prior work changed: '+name
    return len(m)


spec=importlib.util.spec_from_file_location('frozen_path_detector',BASE/'classifiers.py')
OLD=importlib.util.module_from_spec(spec);spec.loader.exec_module(OLD)


def stable_hash(value):return sha256(('CS520-content-pilot-v1|'+value).encode())
