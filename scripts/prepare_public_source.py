"""Create an allowlisted public snapshot; never copy credentials or original Git."""
import hashlib, json, shutil, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
target=ROOT/'runtime/public-source'
target.mkdir(parents=True,exist_ok=True)
files=['README.md','LICENSE','LICENSE_NOTES.md','THIRD_PARTY_NOTICES.md','requirements.txt','requirements-dev.txt','pyproject.toml','.gitattributes']
for name in files: shutil.copy2(ROOT/name,target/name)
for directory in ['app','fixtures','tests','scripts','source-visual-1074']:
    shutil.copytree(ROOT/directory,target/directory,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
(target/'.gitignore').write_text('.venv/\n__pycache__/\n.pytest_cache/\nruntime/\n.netlify/\n.env*\n',encoding='utf-8')
for directory in ['evidence','submission','docs']:(target/directory).mkdir(exist_ok=True)
for name in ['SOURCE_MAP.json','browser-checks.json','test-results.txt']:
    shutil.copy2(ROOT/'evidence'/name,target/'evidence'/name)
for name in ['DEVPOST_EN.md','CONTRIBUTIONS.md','MANUAL_OWNER_ACTIONS.md']:
    shutil.copy2(ROOT/'submission'/name,target/'submission'/name)
for name in ['OFFICIAL_RULES_20261113.md','FINALIZATION_PLAN_20261113.md']:
    shutil.copy2(ROOT/'docs'/name,target/'docs'/name)
(target/'OWNER_DECISIONS.json').write_text(json.dumps({'recorded':'2026-11-13','source':'Owner confirmed in competition chat and Drive OWNER_DECISIONS_CONFIRMED_V2.json','public_source':True,'rights_retained':True,'judge_download_install_run':True,'original_products_read_only':True,'final_submit_authorized':False},indent=2),encoding='utf-8')
for file in target.rglob('*'):
    if file.is_file() and (file.name.startswith('.env') or file.suffix in ['.db','.sqlite','.pem','.key']): raise RuntimeError('Forbidden public file: '+str(file))
manifest=[{'path':p.relative_to(target).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(target.rglob('*')) if p.is_file() and '.git' not in p.parts]
(target/'SOURCE_SNAPSHOT_MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'snapshot':str(target),'files':len(manifest)}))
