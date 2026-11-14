"""Offline MIR v1: measured acoustic features, auditable structural candidates.

No genre/instrument/emotion classifier is run. Structural groups are not
verse/chorus labels. All timestamps refer to the original untrimmed audio.
"""
from pathlib import Path
import os
import sys
import json
import hashlib
import subprocess
import csv
import time

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('NUMBA_CACHE_DIR', str(ROOT / '.cache' / 'numba'))
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.cache' / 'matplotlib'))
os.environ.setdefault('OMP_NUM_THREADS', '4')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '4')
sys.stdout.reconfigure(encoding='utf-8')

import numpy as np
import scipy.ndimage as ndi
import scipy.signal as sig
from scipy.spatial.distance import cdist
import soundfile as sf
import librosa
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

SR, HOP, FFT = 22050, 512, 2048
OUT = ROOT / '02_MIR'
OUT.mkdir(exist_ok=True)
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def save_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def log(message):
    print(time.strftime('%H:%M:%S'), message, flush=True)


def robust_rows(x):
    median = np.median(x, axis=1, keepdims=True)
    scale = np.percentile(x, 75, axis=1, keepdims=True) - np.percentile(x, 25, axis=1, keepdims=True)
    return np.clip((x - median) / np.maximum(scale, 1e-4), -4, 4)


def novelty(features, half_window):
    # Gaussian-weighted difference of left/right contexts. Equivalent to a
    # checkerboard contrast with a linear feature-space similarity kernel.
    length = features.shape[1]
    curve = np.zeros(length)
    w = np.exp(-0.5 * (np.arange(half_window) / (half_window / 2)) ** 2)
    w /= w.sum()
    for i in range(half_window, length-half_window):
        left = features[:, i-half_window:i] @ w[::-1]
        right = features[:, i:i+half_window] @ w
        curve[i] = np.sqrt(np.mean((right-left) ** 2))
    curve = ndi.gaussian_filter1d(curve, .7)
    return curve / max(np.percentile(curve[curve > 0], 95), 1e-8)


def main():
    source = ROOT / '01_输入' / '周杰伦 - 晴天.flac'
    wave_path = ROOT / '01_输入' / '晴天_分析用_22050Hz_mono.wav'
    source_info = sf.info(source)
    source_hash = hashlib.file_digest(source.open('rb'), 'sha256').hexdigest()
    manifest_path = ROOT / '01_输入' / 'source_manifest.json'
    if manifest_path.exists():
        prior_hash = json.loads(manifest_path.read_text(encoding='utf-8'))['sha256']
        if source_hash != prior_hash:
            raise SystemExit('源音频与本实验输入哈希不一致。请另建实验，避免误用现有缓存和分段。')
    save_json(ROOT / '01_输入' / 'source_manifest.json', {
        'source_path': source.relative_to(ROOT).as_posix(), 'sha256': source_hash,
        'duration_seconds': source_info.duration, 'sample_rate': source_info.samplerate,
        'channels': source_info.channels, 'subtype': source_info.subtype,
        'analysis_audio': wave_path.name,
        'preprocessing': 'FFmpeg: stereo arithmetic downmix, resample 22050 Hz, PCM16; no trim, gain normalization or silence removal',
    })
    if not wave_path.exists():
        subprocess.run(['ffmpeg', '-v', 'error', '-i', str(source), '-ac', '1', '-ar', str(SR), '-c:a', 'pcm_s16le', str(wave_path)], check=True)
    log('读取完整音频')
    y, sr = sf.read(wave_path, dtype='float32')
    duration = source_info.duration
    cache = OUT / 'features_full.npz'
    if cache.exists():
        log('读取已保存特征')
        d = dict(np.load(cache))
    else:
        log('计算 STFT、谐波/打击成分、频谱与能量')
        spec = np.abs(librosa.stft(y, n_fft=FFT, hop_length=HOP))
        power = spec ** 2
        harm, perc = librosa.decompose.hpss(spec, margin=2.0)
        rms = librosa.feature.rms(y=y, frame_length=FFT, hop_length=HOP)[0]
        dbfs = 20*np.log10(np.maximum(rms, 1e-8))
        mel = librosa.feature.melspectrogram(S=power, sr=sr, n_mels=64)
        mfcc = librosa.feature.mfcc(S=librosa.power_to_db(mel), n_mfcc=20)
        chroma = librosa.feature.chroma_stft(S=harm**2, sr=sr, n_fft=FFT, hop_length=HOP)
        centroid = librosa.feature.spectral_centroid(S=spec, sr=sr)[0]
        flatness = librosa.feature.spectral_flatness(S=spec)[0]
        contrast = librosa.feature.spectral_contrast(S=spec, sr=sr)
        onset = librosa.onset.onset_strength(S=librosa.power_to_db(librosa.feature.melspectrogram(S=perc**2, sr=sr)), sr=sr, hop_length=HOP)
        freq = librosa.fft_frequencies(sr=sr, n_fft=FFT)
        total = np.maximum(power.sum(axis=0), 1e-12)
        bands = np.array([power[(freq>=lo)&(freq<hi)].sum(axis=0)/total for lo,hi in [(20,250),(250,2000),(2000,8000)]])
        percussive_ratio = (perc**2).sum(axis=0)/np.maximum((perc**2+harm**2).sum(axis=0),1e-12)
        d = dict(rms=rms, dbfs=dbfs, mfcc=mfcc, chroma=chroma, centroid=centroid, flatness=flatness,
                 contrast=contrast, onset=onset, bands=bands, percussive_ratio=percussive_ratio,
                 frame_times=librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=HOP))
        np.savez_compressed(cache, **d)
    times = d['frame_times']
    log('节拍跟踪：检查倍速/半速候选')
    tempo_candidates = []
    for initial in [70, 100, 140]:
        tempo, beats = librosa.beat.beat_track(onset_envelope=d['onset'], sr=sr, hop_length=HOP, start_bpm=initial, trim=False)
        tempo_candidates.append({'start_bpm_prior':initial, 'tempo_bpm':float(np.asarray(tempo).ravel()[0]),
            'beat_count':len(beats), 'beat_frames':beats.tolist()})
    chosen = tempo_candidates[1]
    beat_frames = np.array(chosen['beat_frames'], dtype=int)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=HOP)
    onset_frames = librosa.onset.onset_detect(onset_envelope=d['onset'], sr=sr, hop_length=HOP, backtrack=False)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=HOP)
    save_json(OUT/'beats_and_onsets.json', {
        'tempo_candidates':tempo_candidates, 'selected_candidate_index':1,
        'selection_rule':'default start_bpm=100 estimate; alternatives retained, no manual tapping performed',
        'tempo_bpm':chosen['tempo_bpm'], 'beats_seconds':beat_times.tolist(),
        'onsets_seconds':onset_times.tolist(),
        'downbeats':None, 'meter':None,
        'caveat':'beat estimates are not verified downbeats; onsets are detected transients, not isolated drum hits or melody notes'})
    log('构建节拍同步特征、多尺度变化与分段候选')
    sync_frames = np.unique(np.r_[0, beat_frames, len(times)-1])
    sync_times = times[sync_frames]
    chroma_s = librosa.util.sync(d['chroma'], sync_frames, aggregate=np.median, pad=False)
    mfcc_s = librosa.util.sync(d['mfcc'][1:14], sync_frames, aggregate=np.median, pad=False)
    acoustic_s = librosa.util.sync(np.vstack([d['dbfs'],d['centroid'],d['percussive_ratio']]), sync_frames, aggregate=np.median, pad=False)
    # Feature blocks carry comparable weight, not 13x weight for MFCC.
    feature = np.vstack([robust_rows(chroma_s)/np.sqrt(12), robust_rows(mfcc_s)/np.sqrt(13), robust_rows(acoustic_s)/np.sqrt(3)*.6])
    grid_times = sync_times[:-1]
    curves = np.array([novelty(feature, half) for half in [4,8,16]])
    combined = .2*curves[0]+.45*curves[1]+.35*curves[2]
    peaks, props = sig.find_peaks(combined, prominence=.10, distance=max(2, round(5/(60/chosen['tempo_bpm']))))
    aggl = {}
    for k in [8,10,12,14,16]:
        b = librosa.segment.agglomerative(feature, k=k)
        aggl[str(k)] = [float(grid_times[i]) for i in b]
    candidates = []
    for idx,p in enumerate(peaks):
        t = float(grid_times[p])
        if t < 4 or t > duration-3:
            continue
        support = sum(any(abs(v-t)<=2.0 for v in b[1:]) for b in aggl.values())
        candidates.append({'time':round(t,3),'novelty':round(float(combined[p]),3),
            'prominence':round(float(props['prominences'][idx]),3),'agglomerative_support_out_of_5':support})
    save_json(OUT/'boundary_candidates.json', {'method':'multi-scale beat-synchronous feature contrast + temporal Ward clustering',
        'half_windows_beats':[4,8,16], 'clustering_candidates':aggl, 'candidates':candidates,
        'meaning':'algorithmic candidates; support is parameter agreement, not calibrated probability'})
    # Default candidates, review may replace via separate config without editing measurements.
    accepted = [c['time'] for c in candidates if (c['agglomerative_support_out_of_5']>=2 and c['prominence']>=.13) or c['prominence']>=.38]
    chosen_boundaries = [0.0]
    for b in accepted:
        if b-chosen_boundaries[-1]>=10 and duration-b>=6:
            chosen_boundaries.append(b)
    chosen_boundaries.append(duration)
    review_path=OUT/'segmentation_review.json'
    if review_path.exists():
        review=json.loads(review_path.read_text(encoding='utf-8'))
        chosen_boundaries=review['boundaries_seconds']
    else:
        review={'status':'automatic_draft', 'boundaries_seconds':chosen_boundaries,
                'review_method':'not yet reviewed', 'functional_labels_verified':False}
    np.savez_compressed(OUT/'structure_features.npz', features=feature, times=grid_times, novelty=curves, combined=combined)
    save_json(OUT/'segmentation_selected.json', review)
    # Export frame data at 0.5 s for LLM-adjacent inspection, retain full data separately.
    with (OUT/'continuous_features_0p5s.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f); w.writerow(['time_seconds','rms_dbfs','centroid_hz','low_20_250_ratio','mid_250_2000_ratio','high_2000_8000_ratio','hpss_percussive_ratio','onset_strength'])
        for t in np.arange(0,duration,.5):
            m=(times>=t)&(times<t+.5)
            w.writerow([round(t,3),*np.round([np.mean(d['dbfs'][m]),np.mean(d['centroid'][m]),*np.mean(d['bands'][:,m],axis=1),np.mean(d['percussive_ratio'][m]),np.mean(d['onset'][m])],5)])
    segments=[]
    for i,(start,end) in enumerate(zip(chosen_boundaries[:-1],chosen_boundaries[1:])):
        mask=(times>=start)&(times<end)
        section_beats=beat_times[(beat_times>=start)&(beat_times<end)]
        q=np.percentile(d['dbfs'][mask],[10,50,90])
        third=(end-start)/3
        early=(times>=start)&(times<start+third)
        late=(times>=end-third)&(times<end)
        median_rms=float(np.median(d['rms'][mask]))
        acoustic={
            'rms_dbfs_p10_p50_p90':np.round(q,3).tolist(),
            'energy_percentile_within_track':round(float(np.mean(d['rms']<=median_rms)*100),1),
            'energy_change_last_vs_first_third_db':round(float(np.median(d['dbfs'][late])-np.median(d['dbfs'][early])),3),
            'spectral_centroid_hz_median':round(float(np.median(d['centroid'][mask])),1),
            'spectral_flatness_median':round(float(np.median(d['flatness'][mask])),6),
            'frequency_band_energy_ratios_mean':dict(zip(['20_250_hz','250_2000_hz','2000_8000_hz'],np.round(np.mean(d['bands'][:,mask],axis=1),4).tolist())),
            'hpss_percussive_ratio_median':round(float(np.median(d['percussive_ratio'][mask])),4),
            'detected_onsets_per_second':round(float(np.sum((onset_times>=start)&(onset_times<end))/(end-start)),3),
            'beat_interval_bpm_median':round(float(60/np.median(np.diff(section_beats))),2) if len(section_beats)>2 else None,
            'beat_interval_coefficient_of_variation':round(float(np.std(np.diff(section_beats))/np.mean(np.diff(section_beats))),4) if len(section_beats)>2 else None,
            'chroma_mean':np.round(np.mean(d['chroma'][:,mask],axis=1),4).tolist()
        }
        segments.append({'id':f'S{i+1:02d}','start_seconds':round(start,3),'end_seconds':round(end,3),
            'duration_seconds':round(end-start,3),'functional_label':None,
            'acoustic_measurements':acoustic,
            'unmeasured':{'instruments':None,'genre':None,'valence':None,'arousal':None,'lyrics':None,'melody_notes':None,'chords':None}})
    save_json(OUT/'segment_features.json', {'duration_seconds':duration,'sample_rate':SR,'hop_length':HOP,
        'method':'librosa 0.11.0 / signal processing, no pretrained semantic classifiers',
        'global_tempo_bpm_estimate':chosen['tempo_bpm'],'segments':segments})
    # Similarity describes texture/pitch-class averages; does not assert identical melody.
    avg=np.array([np.mean(feature[:,(grid_times>=a)&(grid_times<b)],axis=1) for a,b in zip(chosen_boundaries[:-1],chosen_boundaries[1:])])
    distance=cdist(avg,avg)
    similarity=np.exp(-distance/max(float(np.median(distance[distance>0])),1e-6))
    save_json(OUT/'segment_similarity.json',{'ids':[s['id'] for s in segments],
        'similarity':np.round(similarity,4).tolist(),'meaning':'similarity of mean normalized chroma/MFCC/acoustic features, not verified melodic repetition'})
    log('输出可视化和摘要')
    fig,axes=plt.subplots(4,1,figsize=(16,11),sharex=True,constrained_layout=True)
    axes[0].plot(times,d['dbfs'],lw=.5,color='#326b9c'); axes[0].set_ylabel('RMS / dBFS'); axes[0].set_ylim(-65,0)
    axes[1].plot(times,ndi.gaussian_filter1d(d['centroid'],8),lw=.7,color='#a06145'); axes[1].set_ylabel('频谱质心 / Hz')
    axes[2].stackplot(times,d['bands'],labels=['20–250 Hz','250–2000 Hz','2000–8000 Hz'],colors=['#495d8c','#5b9d9d','#d1b774']); axes[2].set_ylabel('频段能量占比'); axes[2].legend(loc='upper right',ncol=3)
    axes[3].plot(grid_times,combined,color='#815e96'); axes[3].scatter([c['time'] for c in candidates],[c['novelty'] for c in candidates],s=12,color='#815e96'); axes[3].set_ylabel('结构变化指标'); axes[3].set_xlabel('原音源时间 / 秒')
    for ax in axes:
        for b in chosen_boundaries[1:-1]:ax.axvline(b,color='#444444',alpha=.45,lw=.8)
        ax.grid(alpha=.15)
    for seg in segments:
        axes[0].text((seg['start_seconds']+seg['end_seconds'])/2,-4,seg['id'],ha='center',fontsize=9)
    axes[0].set_title('《晴天》离线 MIR：声学特征与 v1 工作分段（非听辨确认的曲式标签）')
    fig.savefig(OUT/'MIR_全曲特征与分段.png',dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,9),constrained_layout=True)
    # Normalize for display only.
    sim=np.exp(-cdist(feature.T,feature.T,'sqeuclidean')/max(np.median(cdist(feature.T,feature.T,'sqeuclidean')),1e-6))
    im=ax.pcolormesh(sync_times,sync_times,sim,cmap='magma',vmin=0,vmax=1,shading='flat',rasterized=True)
    for b in chosen_boundaries[1:-1]:ax.axvline(b,color='white',lw=.6,alpha=.5);ax.axhline(b,color='white',lw=.6,alpha=.5)
    ax.set(title='节拍同步特征自相似矩阵',xlabel='时间 / 秒',ylabel='时间 / 秒');fig.colorbar(im,ax=ax,label='特征相似度')
    fig.savefig(OUT/'MIR_自相似矩阵.png',dpi=150);plt.close(fig)
    with (OUT/'segments.tsv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f,delimiter='\t');w.writerow(['段落','起点秒','终点秒','时长秒','能量百分位','RMS中位dBFS','质心Hz','起音每秒','打击成分指标'])
        for s in segments:
            a=s['acoustic_measurements'];w.writerow([s['id'],s['start_seconds'],s['end_seconds'],s['duration_seconds'],a['energy_percentile_within_track'],a['rms_dbfs_p10_p50_p90'][1],a['spectral_centroid_hz_median'],a['detected_onsets_per_second'],a['hpss_percussive_ratio_median']])
    log(json.dumps({'tempo':chosen['tempo_bpm'],'segments':[(s['id'],s['start_seconds'],s['end_seconds']) for s in segments]},ensure_ascii=False))


if __name__=='__main__':main()
