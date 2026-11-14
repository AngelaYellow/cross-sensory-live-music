"""Build a local auditable report with original generated images and segment listening."""
from pathlib import Path
import json,html

ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'03_LLM输入/song_visual_input.json').read_text(encoding='utf-8'))
plan=json.loads((ROOT/'04_视觉方案与提示词/visual_plan.json').read_text(encoding='utf-8'))
esc=html.escape
cards=[]
for s in plan['segments']:
    a=s['music_evidence'];sid=s['id']
    cards.append(f'''<article id="{sid}">
    <a class="image" href="{esc(s['image_file'])}" target="_blank"><img loading="lazy" src="{esc(s['image_file'])}" alt="{sid} {esc(s['title'])}的抽象粒子视觉概念图"></a>
    <div class="text"><div class="cardhead"><div><span class="sid">{sid} · {esc(s['time_range_display'])}</span><h2>{esc(s['title'])}</h2></div><button data-id="{sid}" data-start="{s['start_seconds']}" data-end="{s['end_seconds']}">试听该段</button></div>
    <p class="metrics">能量百分位 <strong>{a['energy_percentile_within_track']}</strong> · 质心 <strong>{a['spectral_centroid_hz_median']:.0f} Hz</strong> · 起音 <strong>{a['detected_onsets_per_second']:.2f}/秒</strong></p>
    <p>{esc(s['design_rationale'])}</p>
    <details><summary>查看变化设想、衔接与提示词</summary><p><b>运动设想：</b>{esc(s['motion_proposal'])}</p><p><b>衔接：</b>{esc(s['continuity'])}</p><p>以上属于设计选择，静态图未验证运动或音画同步。</p><a href="04_视觉方案与提示词/{sid}_imagegen_prompt.txt">打开完整生图提示词</a><pre>{esc(json.dumps(a,ensure_ascii=False,indent=2))}</pre></details></div></article>''')
page='''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>晴天 · MIR到AI视觉 · 临时测试v1</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#0c1014;color:#e6ebef;font:16px/1.65 "Microsoft YaHei",system-ui,sans-serif}main{max-width:1220px;margin:auto;padding:36px 24px 70px}header{padding-bottom:24px;border-bottom:1px solid #2c353e}.eyebrow,.sid{color:#a8becb;font-size:13px;letter-spacing:.05em}h1{font-size:36px;line-height:1.3;margin:10px 0 18px;font-weight:600}h2{font-size:22px;line-height:1.4;margin:5px 0 0}p{margin:12px 0}a{color:#9ccee6}nav{display:flex;flex-wrap:wrap;gap:12px 24px;margin-top:20px}.note{max-width:960px;color:#b4c1cb}.player{position:sticky;top:0;z-index:2;background:#10171f;border-bottom:1px solid #36424c;padding:12px 0;display:flex;align-items:center;gap:20px;flex-wrap:wrap}audio{max-width:100%;width:450px;height:42px}.player p{margin:0;font-size:14px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:34px 24px;margin-top:28px}article{min-width:0;background:#111820;border:1px solid #27313a;border-radius:10px;overflow:hidden;scroll-margin-top:100px}article.selected{border-color:#9ccee6}.image{display:block;background:#000}img{display:block;width:100%;height:auto}.text{padding:18px 20px 22px}.cardhead{display:flex;justify-content:space-between;align-items:center;gap:12px}.metrics{font-size:13px;color:#aebfcb}button{border:1px solid #687d8c;background:#172a38;color:#e7f5ff;padding:9px 13px;border-radius:6px;font:inherit;font-size:14px;white-space:nowrap;cursor:pointer}button:hover{background:#26475b}button:focus-visible,a:focus-visible,summary:focus-visible{outline:2px solid #b3dcef;outline-offset:4px}details{margin-top:14px;border-top:1px solid #303b45;padding-top:12px}summary{cursor:pointer;color:#b9d1df;font-size:14px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;color:#b7c5cf}.chart{margin:36px 0 18px;background:#fff}.footer{margin-top:30px;color:#aebdc8;font-size:14px}@media(max-width:760px){main{padding:22px 14px}.grid{grid-template-columns:1fr}h1{font-size:28px}.player{gap:6px}audio{width:100%}.text{padding:16px}.cardhead{align-items:flex-start}}
</style></head><body><main>
<header><div class="eyebrow">本地实验 · 2026-11-14 · v1</div><h1>《晴天》从音乐特征到视觉方案</h1>
<p>完整音频分析 → 15个声学工作段 → 文字LLM视觉设计 → 15张imagegen概念图</p>
<p class="note">这是一轮可追溯的视觉探索。边界已检查信号证据，尚未人工听辨确认曲式；没有把未测量的乐器、情绪或歌词填成事实。每张图代表一个段落的设计状态，不是动态效果或实时粒子系统。</p>
<nav><a href="README.md">使用说明</a><a href="03_LLM输入/逐段音乐描述.md">逐段音乐描述</a><a href="03_LLM输入/song_visual_input.json">给文字LLM的完整输入</a><a href="04_视觉方案与提示词/整曲视觉方案.md">完整视觉方案</a><a href="方法与来源.md">方法与边界</a></nav></header>
<div class="player"><audio id="audio" controls preload="metadata" src="01_输入/晴天_分析用_22050Hz_mono.wav"></audio><p id="status" aria-live="polite">点击任一“试听该段”，播放至该段末尾自动暂停。</p><button id="full">从头播放整曲</button></div>
<section class="grid" aria-label="按时间排列的15段视觉概念">'''+''.join(cards)+'''</section>
<div class="chart"><img loading="lazy" src="02_MIR/MIR_全曲特征与分段.png" alt="全曲RMS、频谱质心、频段比例和结构变化曲线"></div>
<p class="footer">节拍估计约136 BPM，保留68 BPM半速解释。颜色和形态来自本轮美术选择，不是音频测量的唯一答案。点击概念图可以查看原始PNG。所有资源在本地读取，无网络请求。</p>
</main><script>
const audio=document.getElementById('audio');let segmentEnd=null;
document.querySelectorAll('[data-start]').forEach(button=>button.addEventListener('click',async()=>{
 segmentEnd=Number(button.dataset.end);audio.currentTime=Number(button.dataset.start);
 document.querySelectorAll('article').forEach(a=>a.classList.toggle('selected',a.id===button.dataset.id));
 document.getElementById('status').textContent=button.dataset.id+' · 正在播放选定段落';
 try{await audio.play();}catch(e){document.getElementById('status').textContent='请点击音频播放器的播放按钮。';}
}));
audio.addEventListener('timeupdate',()=>{if(segmentEnd!==null&&audio.currentTime>=segmentEnd){audio.pause();segmentEnd=null;document.getElementById('status').textContent='该段试听结束，可选择下一段。';}});
document.getElementById('full').addEventListener('click',async()=>{segmentEnd=null;audio.currentTime=0;document.getElementById('status').textContent='整曲播放 · 图片保持分段陈列';try{await audio.play();}catch(e){document.getElementById('status').textContent='请点击音频播放器的播放按钮。';}});
</script></body></html>'''
(ROOT/'预览.html').write_text(page,encoding='utf-8')
print('report written, '+str(len(cards))+' segment cards')
