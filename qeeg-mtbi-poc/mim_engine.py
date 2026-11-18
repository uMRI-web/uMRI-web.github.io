from __future__ import annotations
import json, re
import numpy as np
from scipy.signal import butter, sosfiltfilt, resample_poly
from scipy.signal.windows import dpss

RAW_COLUMNS=[
 ("Fp1-A1","Fp1"),("Fp2-A2","Fp2"),("F7-A1","F7"),("F8-A2","F8"),
 ("C3-A1","C3"),("C4-A2","C4"),("T3-A1","T3"),("T4-A2","T4"),
 ("T5-A1","T5"),("T6-A2","T6"),("O1-A1","O1"),("O2-A2","O2")
]
LEFT_BIPOLAR=[
 ("Fp1","F7","Fp1-F7"),("F7","T3","F7-T3"),("T3","T5","T3-T5"),
 ("T5","O1","T5-O1"),("Fp1","C3","Fp1-C3")
]
RIGHT_BIPOLAR=[
 ("Fp2","F8","Fp2-F8"),("F8","T4","F8-T4"),("T4","T6","T4-T6"),
 ("T6","O2","T6-O2"),("Fp2","C4","Fp2-C4")
]
BANDS={"theta":(4.0,8.0),"alpha":(8.0,12.0),"beta":(12.0,30.0)}
EMATS_REQUIRED=["Fp1","Fp2","F3","F4","C3","C4","P3","P4","O1","O2","F7","F8","T3","T4","T5","T6","Fz","Cz","Pz"]

def _read_m00(path):
    with open(path,"r",encoding="utf-8",errors="replace") as f:
        header=f.readline().strip()
        cols=f.readline().strip().split()
    m=re.search(r"SamplingInterval\\[ms\\]=([0-9.]+)",header)
    sf=1000.0/float(m.group(1)) if m else 500.0
    use=[];names=[]
    for source,name in RAW_COLUMNS:
        if source not in cols:
            raise ValueError("必要な列がありません: "+source)
        use.append(cols.index(source));names.append(name)
    x=np.loadtxt(path,skiprows=2,usecols=use,dtype=float)
    if x.ndim==1:x=x[None,:]
    x=x[np.all(np.isfinite(x),axis=1)]
    return x.T,names,sf

def _bipolar(x,names):
    idx={n:i for i,n in enumerate(names)}
    out=[];outnames=[]
    for a,b,n in LEFT_BIPOLAR+RIGHT_BIPOLAR:
        out.append(x[idx[a]]-x[idx[b]])
        outnames.append(n)
    return np.asarray(out,float),outnames

def _preprocess(x,sf,skip_sec=60.0,duration_sec=180.0,target_sfreq=250.0):
    start=int(round(skip_sec*sf))
    n=int(round(duration_sec*sf))
    if x.shape[1] < start+n:
        if x.shape[1] <= start+int(60*sf):
            raise ValueError("60秒除外後の記録長が短すぎます")
        n=x.shape[1]-start
    x=x[:,start:start+n]
    sos=butter(4,[1.0,45.0],btype="bandpass",fs=sf,output="sos")
    x=sosfiltfilt(sos,x,axis=1)
    if abs(sf-target_sfreq)>1e-9:
        up=int(round(target_sfreq));down=int(round(sf))
        g=np.gcd(up,down);up//=g;down//=g
        x=resample_poly(x,up,down,axis=1)
        sf=target_sfreq
    epn=int(round(2.0*sf))
    n_ep=x.shape[1]//epn
    x=x[:,:n_ep*epn].reshape(x.shape[0],n_ep,epn).transpose(1,0,2)
    score=np.ptp(x,axis=2).max(axis=1)
    med=float(np.median(score));mad=float(np.median(np.abs(score-med)))
    if mad>0:
        lim=med+6.0*1.4826*mad
        keep=score<=lim
        if keep.sum()<max(20,int(0.5*n_ep)): keep=np.ones(n_ep,dtype=bool)
    else:
        keep=np.ones(n_ep,dtype=bool)
    return x[keep],sf,start,start+n,n_ep,int((~keep).sum())

def _invsqrt_sym(a):
    a=(a+a.T)/2
    vals,vecs=np.linalg.eigh(a)
    floor=max(float(vals.max())*1e-9,1e-12)
    vals=np.maximum(vals,floor)
    return (vecs*(1/np.sqrt(vals)))@vecs.T

def _multitaper_csd(epochs,sf):
    n=epochs.shape[-1]
    tapers=dpss(n,NW=4.0,Kmax=7,sym=False)
    win=epochs[:,:,None,:]*tapers[None,None,:,:]
    fx=np.fft.rfft(win,axis=-1)
    csd=np.einsum("ectf,edtf->fcd",fx,np.conj(fx),optimize=True)/(epochs.shape[0]*tapers.shape[0])
    freqs=np.fft.rfftfreq(n,d=1.0/sf)
    return freqs,csd

def _mim_spectrum(csd,n_seed):
    vals=np.zeros(csd.shape[0],float)
    for fi,C in enumerate(csd):
        Ta=_invsqrt_sym(np.real(C[:n_seed,:n_seed]))
        Tb=_invsqrt_sym(np.real(C[n_seed:,n_seed:]))
        T=np.zeros((C.shape[0],C.shape[0]),float)
        T[:n_seed,:n_seed]=Ta
        T[n_seed:,n_seed:]=Tb
        D=T@C@T
        E=np.imag(D[:n_seed,n_seed:])
        vals[fi]=float(np.trace(E@E.T))
    return vals

def _band_means(freqs,mim):
    out={}
    for name,(lo,hi) in BANDS.items():
        mask=(freqs>=lo)&(freqs<=hi)
        raw=float(np.mean(mim[mask]))
        out[name]={"raw":raw,"normalized":raw/10.0}
    return out

def analyze_m00(path):
    raw,names,orig_sf=_read_m00(path)
    bipolar,bnames=_bipolar(raw,names)
    epochs,sf,s0,s1,n_total,n_rej=_preprocess(bipolar,orig_sf)
    freqs,csd=_multitaper_csd(epochs,sf)
    mim=_mim_spectrum(csd,5)
    present=set(names)
    matched=[c for c in EMATS_REQUIRED if c in present]
    missing=[c for c in EMATS_REQUIRED if c not in present]
    return {
      "source":str(path).split("/")[-1],
      "original_sfreq":float(orig_sf),
      "analysis_sfreq":float(sf),
      "used_start_sec":s0/orig_sf,
      "used_end_sec":s1/orig_sf,
      "epochs_total":int(n_total),
      "epochs_rejected":int(n_rej),
      "epochs_kept":int(epochs.shape[0]),
      "bipolar_channels":bnames,
      "mim":_band_means(freqs,mim),
      "emats":{
        "matched_channels":len(matched),
        "match_percent":100*len(matched)/len(EMATS_REQUIRED),
        "missing_channels":missing,
        "direct_inference":False,
        "retrain_route":"可能。TUEG/EMATS側でも同じ10本の双極導出を作り、250 Hz・3分の同一入力へ揃えてTBI/Stroke/Normal分類器を再学習する。"
      }
    }

def analyze_m00_json(path):
    return json.dumps(analyze_m00(path),ensure_ascii=False)

def self_test_json():
    rng=np.random.default_rng(42)
    sf=250.0;n=500;n_ep=60;t=np.arange(n)/sf
    e=np.empty((n_ep,10,n),float)
    for k in range(n_ep):
        phi=rng.uniform(0,2*np.pi)
        base=np.sin(2*np.pi*10*t+phi)
        lag=np.sin(2*np.pi*10*t+phi+0.7)
        e[k,:5]=base+0.7*rng.standard_normal((5,n))
        e[k,5:]=lag+0.7*rng.standard_normal((5,n))
    freqs,csd=_multitaper_csd(e,sf)
    m=_mim_spectrum(csd,5)
    b=_band_means(freqs,m)
    ok=b["alpha"]["raw"]>b["theta"]["raw"] and b["alpha"]["raw"]>b["beta"]["raw"]
    return json.dumps({"pass":bool(ok),"bands":b},ensure_ascii=False)
