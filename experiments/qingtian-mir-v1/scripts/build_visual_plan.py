"""Persist the design authored by the current Codex LLM from measured input.

This script serializes that authored result; it does not call a text-model API.
Image jobs are executed separately with the native imagegen tool.
"""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'04_视觉方案与提示词'
DEST.mkdir(exist_ok=True)

STATES=[
('S01','微光起伏','全曲相对能量最低且频谱质心较低，选用少量、清晰、安静的结构；不据此判断情绪。',
 'A single slender undulating sheet of icy white pinpoints floats across the lower middle of an immense black void. The sheet gently folds over itself once, with organized rows of tiny dots and only a few filament edges. Extremely sparse satellite specks, restrained glow, pale blue at the fold, much empty black space above and around it. Intimate, delicate scale; no center explosion.',
 '薄片轻微起伏，点沿弧面缓慢移动；开头静音时从黑场显现。','建立全曲共同的点阵薄片主体。'),
('S02','光丝汇入','能量、质心和起音密度较S01提高，增加第二层结构和汇入方向。',
 'The same delicate point-cloud sheet now has a second thinner ribbon approaching it. Two sinuous ribbons of ordered white micro-particles weave past one another without touching, forming a loose elongated S in black space. A subtle cyan edge highlights their approach. Still restrained and airy, with separated foreground and background layers and generous negative space.',
 '第二束粒子沿切向汇入，保持主薄片连续。','延续S01轮廓，增加一个副层。'),
('S03','褶面成形','能量进入本曲中等范围、起音密度继续提高，选择更完整的褶皱曲面。',
 'Three loosely connected folds of the same luminous particle membrane form one open asymmetric sculpture. Fine orderly rows of blue-white dots reveal the surface curvature; thin luminous filaments bridge a few folds. The surface remains transparent and perforated, never solid fabric. Subtle sea-glass cyan and a tiny champagne accent at one junction. Medium scale against deep black, clear silhouette and visible empty center.',
 '褶面逐步张开，小范围节点短暂增强。','由两束光丝发展成连续薄片。'),
('S04','层流交织','较S03更高的质心与打击成分指标支持更清楚的边缘和更多层次；这些视觉对应是本实验选择。',
 'The same open particle membrane unfolds into several interlaced sweeping sheets, a broad diagonal composition with foreground and background clearly separated. Individual white and cyan pinpoints trace ordered curved rows, with occasional filament bundles showing the flow direction. Keep an irregular dark opening and restrained pale gold accents at a few crossings. Crisp middle plane, soft peripheral depth, elegant complexity rather than a chaotic burst.',
 '不同层有相位差的波动，交点局部亮起。','保留S03中央空隙并扩大空间跨度。'),
('S05','向外舒展','段落能量和质心进一步提高，起音密度低于S04；用较宽而连续的展开代替更密碎裂。',
 'A wide flowing fan of the established blue-white particle membranes opens horizontally across a black void. The sculpture consists of long smooth sheets and coherent filament streams, broad spacious curves rather than many sharp fragments. Millions-like fine visible dots remain individually resolved, thin champagne highlights along selected edges, spacious gaps between the sheets, a luminous yet controlled crest. The whole form is graceful and expansive, fully abstract.',
 '扩大曲面跨度，粒子流保持连续而不过度闪动。','从交织转向较宽的展开状态。'),
('S06','光场展开','能量百分位68.2、质心2401.5 Hz、打击成分指标0.0498，为本轮较强且较明亮的声学段，选择充分展开的主状态。',
 'The fully opened state of an abstract organic particle sculpture: several enormous curling, pleated membranes of icy white micro-points sweep outward around a large irregular hollow. Precise dotted rows follow every curve, interwoven hair-thin glowing streams connect the layers, and sparse particles peel away at the tips. Cold white and electric ice-blue dominate with restrained mint and pale champagne accents. Strong large-scale silhouette, beautiful structured complexity, deep black pockets, cinematic foreground and background separation. Spectacular but not overexposed; no literal flower, no tunnel and no centered starburst.',
 '主薄片保持展开，局部点群随起音响应；充分展开状态不等于全程频闪。','作为全曲统一风格的锚定图；S12将回到同类形态。'),
('S07','舒展后的长流','能量较S06略低、起音密度减少，质心保持接近；选择拉长并疏开，而不是完全换主题。',
 'The fully opened particle membranes now stretch into long sweeping ribbons that stream across the frame, keeping the same white-blue dotted surface material. Fewer tight folds, larger separations, an elongated flowing crest and a few detached strands receding into depth. Sparse tiny pale-gold nodes punctuate the curves. Rich surface detail but calmer overall density, extensive black gaps, entirely abstract and nonfigurative.',
 '展开薄片拉长，外围逐渐稀疏。','继承S06材质并减少紧密褶皱。'),
('S08','回收留白','141.8秒附近多方法支持边界，能量明显降低、质心下降，选择收拢和增加留白；起音仍存在。',
 'A deliberate contraction of the same particle sculpture into two small curved translucent folds suspended in a wide black space. Their contours remain sharply legible through fine white dots and faint cyan filaments. Preserve tiny patterned micro-details within the folds but remove the grand surrounding fan. Much more negative space than the previous expanded state, soft restrained glow, a quiet compact knot with a narrow opening, no opaque object.',
 '大形态回收，保留细小局部事件；不表现为完全停止。','从S07连续回收，保持同一材料。'),
('S09','再度交织','能量从21.4升到62.7百分位，质心和起音指标上升；平均声学特征接近S04，复用交织母题。',
 'The compact white-blue particle folds re-open into three assertive interwoven ribbons, recalling the earlier layered weaving state but with a fuller foreground sweep. Ordered dots trace flexible membranes; several fine streams branch and reconnect around an asymmetrical black gap. Pale mint accents and a restrained champagne point at a crossing. Clear layered depth, confident scale, highly detailed but still open and transparent.',
 '从收拢状态重新展开，交织节点增强。','回访S04的交织母题，不宣称音乐旋律完全相同。'),
('S10','交织加密','与S09能量接近，质心和打击成分指标略高，选择局部纹理加密，保持整体构图家族。',
 'A close variation of the reopened interwoven particle sculpture: the same three principal ribbons remain, while fine luminous threads and tiny dotted tributaries become denser at selected junctions. Do not increase the overall size dramatically. White, ice-blue and muted mint with very small pale-gold spark nodes. Strong readable flow paths, transparent membranes, sparse surrounding dust and deep black negative space.',
 '整体保持，局部点列和边缘短暂活跃。','保持S09主体，只细化局部纹理。'),
('S11','开阔回旋','能量较高、质心2363.3 Hz，而起音密度比S10低；选择宽阔回旋与连续曲面。',
 'The woven streams open into a broad asymmetrical rolling wave of several luminous particle sheets, curling around a dark void with an off-center luminous crest. Emphasize long continuous trajectories and spacious curvature rather than many small isolated sparks. Fine icy-white dots, blue filament edges, subtle champagne at the crest, crisp readable structure against pure black. A wide sculptural view with layered depth.',
 '长轨迹回旋，保持宽阔展开；局部细碎响应减少。','继承已形成的光丝与薄片结构。'),
('S12','光场再现','与S06平均特征相似度0.7873、时序特征相关0.6374，且能量与质心接近，回访S06展开状态；不是已确认副歌标签。',
 'Return to the same fully opened organic point-cloud membrane sculpture as the established maximum-expansion reference. Keep its pleated surfaces, large irregular hollow, blue-white dotted material, fine connecting streams and broad scale recognizable. This return has slightly more crisp tiny glints along outer rims and a modest mint-to-champagne accent at a few intersections, not a new object. Powerful structured expansion, generous black pockets, controlled bloom, no flower and no radial explosion.',
 '复现S06主形态，增强少量边缘响应。','明确继承S06，保留可辨认的视觉重复。'),
('S13','余势延伸','平均特征接近S07但时间序列相关较低，不将其视为精确重复；以同材质的另一种展开收束设计回应。',
 'A new variation within the same white-blue particle membrane family: the broad open sheets twist into two long offset arcs and a lighter trailing ribbon. Keep their fine ordered point rows and filament edges recognizable. One arc passes forward, one recedes, leaving a clear asymmetric void. Restrained pale champagne specks dissolve at the outer tips. Sustained expansive scale, elegant layered continuity, fully abstract.',
 '两条长弧产生前后错位，外围点群逐步脱离。','与S07共享长流语言，但不复制其完整构图。'),
('S14','细点回落','242.5秒处多方法支持变化，能量下降但起音密度较高；用更小的整体和清楚的局部颗粒形成差异。',
 'The large particle membranes reduce to a smaller broken arc and a delicate thin sheet, surrounded by many individually distinct but sparse pinpricks. Lower overall luminosity and scale, still crisp rhythmic-looking micro-patterns along the edges. Cool white and faded blue with the faintest warm accents. Large black gaps dominate, no diffuse fog blanket, a clean legible reduction of the earlier sculpture.',
 '整体逐渐缩小，局部细点仍保留事件响应。','从S13减小尺度，保留细颗粒结构。'),
('S15','微光消隐','尾部能量显著下降并包含结束静音；保留最后一束结构与逐渐散开的少量光点。',
 'The final residual state of the same abstract particle artwork: one very thin incomplete arc of faint icy-white points and a small wisp of organized blue-white filament, slowly dispersing into an almost empty black field. Only a few detached micro-particles remain. Extremely restrained luminosity, clear miniature structure, subtle depth and abundant pure black negative space. No starscape, no text, no literal object. A beautiful barely-there ending image before black.',
 '最后几秒随实测能量衰减，粒子停止补充并消隐至黑。','回到S01的稀疏程度，结束于黑场。')
]

COMMON='''Use case: stylized-concept. Asset type: a single full-frame landscape key visual for an abstract music-art sequence, ideally 16:9. Create a new composition guided by the reference images, not a reproduction of the screenshot. Reference images are STYLE references: take only their small luminous particles, organically curved point rows, translucent thin surfaces, fine filaments, black negative space and depth. Ignore all screenshot interface, text, play buttons, logos and concrete plant/person subjects. Shared material: fine resolved light points with delicate connecting filaments, organized into a plausible three-dimensional open membrane. The image must have a strong large-scale silhouette as well as exquisite microdetail. Soft localized bloom, crisp structural middle plane, restrained peripheral depth of field. It must remain fully abstract, with no identifiable real flower, human, plant stem, architecture, planet, letter, diagram or UI. Do not turn everything into smooth opaque fabric, amorphous smoke, galaxy wallpaper, neon tubes or an unreadable mass. No labels, no text, no borders, no watermark. This is a STATIC art-direction concept, not evidence of a running particle simulation. State-specific visual brief: '''

def main():
    constraints=json.loads((ROOT/'03_LLM输入/视觉约束.json').read_text(encoding='utf-8'))
    if constraints['version']!='v1':
        raise SystemExit('此脚本只记录已被修订的v1纯抽象方案，现已停用，避免覆盖当前语义方向。历史提示词保留作旧图溯源；新方案应读取当前LLM输入后重新设计。')
    data=json.loads((ROOT/'03_LLM输入/song_visual_input.json').read_text(encoding='utf-8'))
    segs={s['id']:s for s in data['segments']}
    refs=[str(ROOT/'01_输入/视觉参考原图'/f'参考_{i:02d}.jpg') for i in [1,5]]
    jobs=[]; plans=[]
    for sid,title,reason,state,motion,continuity in STATES:
        s=segs[sid]
        continuity_note=('Reference image 1 is the established S06 style anchor from this same sequence. Preserve its point-and-filament material and color family, but change the composition, scale and density as instructed in the state-specific brief. Reference images 2 and 3 are the original style screenshots. ' if sid!='S06' else '')
        prompt=continuity_note+COMMON+state
        (DEST/f'{sid}_imagegen_prompt.txt').write_text(prompt,encoding='utf-8')
        plan={'id':sid,'title':title,'start_seconds':s['start_seconds'],'end_seconds':s['end_seconds'],
            'time_range_display':s['time_range_display'],'music_evidence':s['acoustic_measurements'],
            'interpretation_status':'LLM-authored aesthetic choice; not an empirical music-to-color rule',
            'design_rationale':reason,'visual_brief_en':state,'motion_proposal':motion,'continuity':continuity,
            'imagegen_prompt':prompt,'image_status':'pending','image_file':f'05_生成图/{sid}.png'}
        plans.append(plan)
        job_refs=([str(ROOT/'05_生成图/S06.png')]+refs) if sid!='S06' else refs
        jobs.append({'id':sid,'prompt':prompt,'referenced_image_paths':job_refs,'transparent_background':False})
    output={'authoring':'Current Codex conversation LLM, directly reading song_visual_input.json; no separate text-model API call',
        'visual_direction':'同一组粒子褶皱薄片与光丝，按声音状态聚拢、展开、交织、疏散',
        'palette_status':'来自参考图的设计选择，非音频客观推导',
        'image_tool':'native image_gen.imagegen','anchor_segment':'S06','segments':plans}
    (DEST/'visual_plan.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    (DEST/'imagegen_jobs.json').write_text(json.dumps(jobs,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# 文字LLM的视觉设计输出','',output['authoring'],'', '共同主体：'+output['visual_direction'],'',
      '15个工作段各生成1张主图。所有运动都是后续设计设想，静态图不证明音画同步。颜色、空间和形态属于本轮设计选择。','']
    for p in plans:
        lines += [f'## {p["id"]} · {p["time_range_display"]} · {p["title"]}','',
          '**音乐依据与设计理由：** '+p['design_rationale'],'',
          '**画面：** '+p['visual_brief_en'],'',
          '**运动设想：** '+p['motion_proposal'],'',
          '**衔接：** '+p['continuity'],'',
          '完整生图提示词：'+p['id']+'_imagegen_prompt.txt','']
    (DEST/'整曲视觉方案.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({'segments':len(plans),'anchor':'S06'},ensure_ascii=False))

if __name__=='__main__':main()
