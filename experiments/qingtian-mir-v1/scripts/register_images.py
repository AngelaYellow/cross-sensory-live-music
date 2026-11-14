"""Copy native imagegen results unchanged and record provenance."""
from pathlib import Path
import json,sys,shutil,hashlib
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
records=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
manifest_path=ROOT/'05_生成图/generation_manifest.json'
manifest=json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else []
jobs={x['id']:x for x in json.loads((ROOT/'04_视觉方案与提示词/imagegen_jobs.json').read_text(encoding='utf-8'))}
for r in records:
    sid=r['id'];source=Path(r['native_file']);dest=ROOT/f'05_生成图/{sid}.png'
    shutil.copy2(source,dest)
    with Image.open(dest) as im: size=im.size
    row={'id':sid,'tool':'native image_gen.imagegen','source_generated_file':str(source),
        'saved_file':str(dest.relative_to(ROOT)).replace('\\','/'),'pixel_size':size,
        'sha256':hashlib.file_digest(dest.open('rb'),'sha256').hexdigest(),
        'prompt_file':f'04_视觉方案与提示词/{sid}_imagegen_prompt.txt',
        'reference_files':jobs[sid]['referenced_image_paths'],
        'image_type':'static concept image','model_id':None,'seed':None,
        'generation_settings_note':'native tool does not expose model version or seed; preserve image and exact prompt'}
    manifest=[m for m in manifest if m['id']!=sid]+[row]
manifest_path.write_text(json.dumps(sorted(manifest,key=lambda x:x['id']),ensure_ascii=False,indent=2),encoding='utf-8')
plan_path=ROOT/'04_视觉方案与提示词/visual_plan.json'
plan=json.loads(plan_path.read_text(encoding='utf-8'))
for s in plan['segments']:
    if any(m['id']==s['id'] for m in manifest):s['image_status']='generated'
plan_path.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'registered':len(records),'total_saved':len(manifest)},ensure_ascii=False))
