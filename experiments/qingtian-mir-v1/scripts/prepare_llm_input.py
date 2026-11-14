"""Prepare evidence-only LLM input; no new musical facts are generated here."""
from pathlib import Path
import json
import numpy as np
from scipy.spatial.distance import cdist

ROOT=Path(__file__).resolve().parents[1]

def load(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
def save(path,obj):(ROOT/path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def clock(t):return f'{int(t)//60:02d}:{t%60:05.2f}'

def main():
    features=load('02_MIR/segment_features.json')
    boundaries=load('02_MIR/boundary_candidates.json')
    beats=load('02_MIR/beats_and_onsets.json')
    similarity=load('02_MIR/segment_similarity.json')
    structure=np.load(ROOT/'02_MIR/structure_features.npz')
    f,t=structure['features'],structure['times']
    segments=features['segments']
    evidence=[]
    for i,s in enumerate(segments):
        a=s['acoustic_measurements']
        if i==0:
            boundary={'status':'audio_start','time':0.0}
        else:
            c=min(boundaries['candidates'],key=lambda c:abs(c['time']-s['start_seconds']))
            boundary={**c,'status':'multi_method_support' if c['agglomerative_support_out_of_5']>=2 else 'novelty_supported_subsection',
                'listening_verified':False,'timing_caveat':'估计边界，不能按毫秒精度解释；模型/窗口选择可能导致偏移'}
        e=a['energy_percentile_within_track']
        energy='较低' if e<25 else ('中等' if e<55 else '较高')
        change=a['energy_change_last_vs_first_third_db']
        trend='末段较开头增强' if change>1.5 else ('末段较开头减弱' if change < -1.5 else '首末三分之一能量中位数接近')
        s['time_range_display']=clock(s['start_seconds'])+'–'+clock(s['end_seconds'])
        s['boundary_evidence']=boundary
        s['descriptive_summary']={
            'energy':f'段落RMS中位值处于全曲帧能量的第{e:.1f}百分位，属于本曲{energy}能量范围',
            'within_segment_trend':f'{trend}，差值{change:+.2f} dB',
            'texture':f'频谱质心中位{a["spectral_centroid_hz_median"]:.1f} Hz；检测起音{a["detected_onsets_per_second"]:.2f}次/秒；HPSS打击成分指标{a["hpss_percussive_ratio_median"]:.4f}',
            'source':'measured_acoustic_features_with_explicit_heuristic_summary',
            'limitations':'能量较高不等于快乐或激动；频谱质心不是旋律音高；起音不是鼓点清单；HPSS成分不是乐器识别'}
        s['similar_sections_by_average_features']=sorted([
            {'id':similarity['ids'][j],'score':v} for j,v in enumerate(similarity['similarity'][i]) if i!=j
        ],key=lambda x:-x['score'])[:2]
        evidence.append({'id':s['id'],'start':s['start_seconds'],'boundary':boundary})
    # Compare temporal patterns for closest pairs as a separate, auditable check.
    pattern_checks=[]
    for first,second in [('S06','S12'),('S07','S13')]:
        s1,s2=[next(s for s in segments if s['id']==x) for x in [first,second]]
        xs=[]
        for s in [s1,s2]:
            m=(t>=s['start_seconds'])&(t<s['end_seconds']);z=f[:,m]
            xs.append(np.array([np.interp(np.linspace(0,1,64),np.linspace(0,1,z.shape[1]),row) for row in z]))
        correlation=float(np.corrcoef(xs[0].ravel(),xs[1].ravel())[0,1])
        pattern_checks.append({'pair':[first,second],'duration_normalized_feature_correlation':round(correlation,4),
            'meaning':'time-resampled standardized feature correlation; supports acoustic-pattern similarity, not lyric/melody identity'})
    save('02_MIR/repetition_checks.json',pattern_checks)
    data={
        'schema_version':'music_visual_input_v1_revision_2',
        'track':{'title':'晴天','artist':'周杰伦','identity_source':'user-provided filename; no external identification',
            **load('01_输入/source_manifest.json')},
        'processing':{'analysis_sample_rate':22050,'hop_length':512,'frame_step_seconds':512/22050,
            'beat_estimate_bpm':features['global_tempo_bpm_estimate'],
            'half_time_alternative_bpm':beats['tempo_candidates'][0]['tempo_bpm'],
            'tempo_caveat':'136/68为拍级解释歧义，未通过人工打拍确认；不据此声称变速',
            'model_scope':'signal processing only; no pretrained semantic MIR models'},
        'segmentation':{'count':len(segments),'status':'signal_reviewed_working_segmentation',
            'human_listening_verified':False,'functional_labels_verified':False,
            'review_description':'Codex核对全曲特征图、自相似矩阵、各边界多粒度聚类支持；保留较细声学变化作为视觉工作段',
            'boundaries_are_not_ground_truth':True},
        'segments':segments,'pattern_similarity_checks':pattern_checks,
        'global_unknowns':['verified_song_form','instrument_inventory','genre_probabilities','valence','arousal','lyrics_alignment','melody_notes','chords'],
        'song_semantics':load('03_LLM输入/歌曲语义补充.json'),
        'semantic_alignment':{'status':'not_aligned_to_local_audio','segments':None},
        'design_constraints_version':load('03_LLM输入/视觉约束.json')['version'],
        'design_task':'使用修订后的视觉约束和歌曲语义补充，先建立主题、意象与关系变化，再结合声学证据设计表现。允许可识别主体，不强制纯抽象。歌词未对齐，不能把全曲语义编造为15段精确标签；全部视觉隐喻标为创作选择。'
    }
    save('03_LLM输入/song_visual_input.json',data)
    lines=['# 《晴天》逐段音乐输入（v1）','',
      '全曲约269.747秒。节拍主估计约136 BPM，另保留68 BPM半速解释。本版有15个声学工作段；没有人工听辨确认的主歌/副歌标签，也没有预训练乐器/情绪模型结果。',
      '', '以下数值来自本地音频。色彩、形态和情绪联想不属于测量结果。','']
    for s in segments:
        lines += [f'## {s["id"]} · {s["time_range_display"]}', '', *['- '+v for k,v in s['descriptive_summary'].items() if k in ['energy','within_segment_trend','texture']],
          '- 边界依据：'+s['boundary_evidence']['status'],
          '- 相似段候选：'+', '.join(x['id'] for x in s['similar_sections_by_average_features']),
          '- 乐器、曲风、情绪值、歌词、音符、和弦：未测量。','']
    (ROOT/'03_LLM输入/逐段音乐描述.md').write_text('\n'.join(lines),encoding='utf-8')
    save('02_MIR/segmentation_review.json',{'status':'signal_reviewed_working_segmentation',
        'boundaries_seconds':[s['start_seconds'] for s in segments]+[data['track']['duration_seconds']],
        'review_method':data['segmentation']['review_description'],'functional_labels_verified':False,
        'human_listening_verified':False,'boundary_reviews':evidence,
        'retained_subsections_reason':'弱跨方法支持的边界仍作为视觉状态候选保留；不将每个工作段宣称为完整曲式段落'})
    print(json.dumps({'segments':len(segments),'pattern_checks':pattern_checks},ensure_ascii=False))

if __name__=='__main__':main()
