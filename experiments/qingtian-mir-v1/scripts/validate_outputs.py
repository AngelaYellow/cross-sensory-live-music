"""Check cross-stage integrity without claiming aesthetic or musicological validation."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote,urlparse
import json,hashlib,math
import numpy as np
import soundfile as sf
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
checks=[]
skipped=[]
def check(name,condition,details=None):
    checks.append({'name':name,'passed':bool(condition),'details':details})
def read(p): return json.loads((ROOT/p).read_text(encoding='utf-8'))
def digest(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
source=read('01_输入/source_manifest.json')
mir=read('02_MIR/segment_features.json')
llm=read('03_LLM输入/song_visual_input.json')
plan=read('04_视觉方案与提示词/visual_plan.json')
jobs=read('04_视觉方案与提示词/imagegen_jobs.json')
manifest=read('05_生成图/generation_manifest.json')
source_path=ROOT/source['source_path']
analysis_path=ROOT/'01_输入'/source['analysis_audio']
if source_path.exists():
    check('source_hash_unchanged',digest(source_path)==source['sha256'])
else:
    skipped.append('Source audio intentionally not distributed; source hash not rechecked.')
if analysis_path.exists():
    info=sf.info(analysis_path)
    check('analysis_audio_same_duration',abs(info.duration-source['duration_seconds'])<1/info.samplerate,info.duration)
    check('analysis_audio_format',info.samplerate==22050 and info.channels==1)
else:
    skipped.append('Analysis WAV not distributed; duration/format and playback not rechecked.')
segs=mir['segments'];ids=[s['id'] for s in segs]
check('15_distinct_segments',len(ids)==15 and len(set(ids))==15)
check('complete_continuous_coverage',abs(segs[0]['start_seconds'])<.001 and abs(segs[-1]['end_seconds']-source['duration_seconds'])<.001 and all(abs(a['end_seconds']-b['start_seconds'])<.001 for a,b in zip(segs,segs[1:])) and all(s['end_seconds']>s['start_seconds'] for s in segs))
for name,rows in [('llm',llm['segments']),('plan',plan['segments']),('jobs',jobs),('images',manifest)]:
    check(name+'_ids_match',sorted(x['id'] for x in rows)==ids)
check('unmeasured_semantics_preserved',all(s['functional_label'] is None and all(x is None for x in s['unmeasured'].values()) for s in llm['segments']))
check('review_limitations_preserved',llm['segmentation']['human_listening_verified'] is False and llm['segmentation']['functional_labels_verified'] is False)
for s,p,l in zip(segs,plan['segments'],llm['segments']):
    check(s['id']+'_music_evidence_matches',s['acoustic_measurements']==p['music_evidence']==l['acoustic_measurements'] and s['start_seconds']==p['start_seconds']==l['start_seconds'] and s['end_seconds']==p['end_seconds']==l['end_seconds'])
for fname in ['features_full.npz','structure_features.npz']:
    with np.load(ROOT/'02_MIR'/fname,allow_pickle=False) as arr:
        numeric={k:v for k,v in arr.items() if np.issubdtype(v.dtype,np.number)}
        check(fname+'_numeric_values_finite',all(np.isfinite(v).all() for v in numeric.values()),list(numeric))
jobmap={j['id']:j for j in jobs}
for item in manifest:
    sid=item['id'];p=ROOT/item['saved_file']
    with Image.open(p) as im:
        size=im.size;fmt=im.format;im.verify()
    check(sid+'_saved_image_integrity',fmt=='PNG' and list(size)==item['pixel_size'] and digest(p)==item['sha256'],{'size':size})
    check(sid+'_exact_prompt_saved',(ROOT/item['prompt_file']).read_text(encoding='utf-8').strip()==jobmap[sid]['prompt'].strip())
    check(sid+'_reference_paths_exist',all((ROOT/x).exists() for x in item['reference_files']))
    check(sid+'_generated_status',next(s for s in plan['segments'] if s['id']==sid)['image_status']=='generated')
class Links(HTMLParser):
    def __init__(self):super().__init__();self.urls=[];self.cards=0
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='article':self.cards+=1
        for key in ('href','src'):
            if key in a:self.urls.append(a[key])
parser=Links();parser.feed((ROOT/'预览.html').read_text(encoding='utf-8'))
missing=[u for u in parser.urls if not urlparse(u).scheme and not u.startswith('#') and not (ROOT/unquote(u.split('#')[0])).exists() and ROOT/unquote(u.split('#')[0])!=analysis_path]
check('report_all_local_links_exist',not missing,missing)
check('report_has_15_cards',parser.cards==15)
report={'scope':'repository file and data integrity only; no claim of song semantics, aesthetic quality, listening or playback validation','passed':all(x['passed'] for x in checks),'check_count':len(checks),'skipped':skipped,'checks':checks}
(ROOT/'logs/repository_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':report['passed'],'check_count':len(checks),'failed':[c for c in checks if not c['passed']]},ensure_ascii=False))
raise SystemExit(0 if report['passed'] else 1)
