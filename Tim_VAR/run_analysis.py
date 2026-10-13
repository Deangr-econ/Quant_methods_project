from pathlib import Path
import json, hashlib, warnings
import numpy as np
import pandas as pd
from scipy import linalg, stats

ROOT = Path(__file__).resolve().parent
if (ROOT / 'package/data').exists():
    ROOT = ROOT / 'package'
DATA = ROOT / 'data/group_data.csv'
OUT = ROOT / 'results'
OUT.mkdir(parents=True, exist_ok=True)
df = pd.read_csv(DATA, parse_dates=['date'])
names = ['ES','CL','GC','NG','C','TY']
markets = {
    'AR': ['ES'],
    'Oil and gold': ['ES','CL','GC'],
    'Gas and Treasury': ['ES','NG','TY'],
    'All commodities': ['ES','CL','GC','NG','C'],
    'Full VAR': names,
}
data = pd.DataFrame({'date': df.date})
for s in names[:-1]: data[s] = df['log_rv5_'+s]
data['TY'] = df.rv_yield_10
assert len(data)==3910 and df.date.is_unique and df.date.is_monotonic_increasing
assert np.isfinite(df.iloc[:,1:].to_numpy()).all()
for s in names[:-1]:
    assert (df['rv5_'+s]>0).all()
    assert np.allclose(df['log_rv5_'+s],np.log(df['rv5_'+s]),rtol=0,atol=1e-12)
assert np.allclose(df.rv_yield_10,df.abs_dyield_10**2,rtol=0,atol=1e-8)
assert np.allclose(df.rv_yield_10.iloc[1:],(100*df.dgs10.diff().iloc[1:])**2,atol=1e-8)
cutoff=pd.Timestamp('2023-07-12')
n0=int((data.date<=cutoff).sum())
assert n0==3127 and len(data)-n0==783
month=data.date.dt.month.to_numpy(); weekday=data.date.dt.weekday.to_numpy()+1
controls=np.column_stack([month==m for m in range(2,13)]+[weekday==d for d in range(2,6)]).astype(float)

def design(d, cols, p, start=None, seasonal=True):
    rows=np.arange(p if start is None else start,len(d))
    X=np.column_stack([np.ones(len(rows))]+[d[v].to_numpy()[rows-j] for j in range(1,p+1) for v in cols])
    if seasonal: X=np.column_stack([X,controls[rows]])
    return X, d[cols].to_numpy()[rows], rows

def fit(X,Y):
    center=X.mean(axis=0); scale=X.std(axis=0)
    center[0]=0;scale[0]=1
    assert (scale>0).all()
    Z=(X-center)/scale
    B=linalg.lstsq(Z,Y,lapack_driver='gelsy')[0]
    b=B/scale[:,None] if B.ndim==2 else B/scale
    b[0]-=center@b
    residual=Y-X@b
    return b,residual

selection=[]
for p in range(1,21):
    X,Y,_=design(data.iloc[:n0],names,p,start=20)
    b,u=fit(X,Y); T=len(Y); K=len(names); k=X.shape[1]
    sign,ld=np.linalg.slogdet(u.T@u/T);assert sign>0
    selection.append(dict(p=p,AIC=ld+2*K*k/T,BIC=ld+np.log(T)*K*k/T,n=T,parameters_per_equation=k))
ic=pd.DataFrame(selection);ic.to_csv(OUT/'lag_selection.csv',index=False)
p_main=int(ic.loc[ic.BIC.idxmin(),'p']);p_aic=int(ic.loc[ic.AIC.idxmin(),'p'])
print('LAG CHOICE',p_main,p_aic,flush=True)

all_accuracy=[]; diagnostics=[]; granger=[]; max_check=0.
def forecast(d,cols,p,seasonal=True,start=None):
    global max_check
    X,Y,rows=design(d,cols,p,start=start,seasonal=seasonal)
    y=Y[:,0];n_fit=int((rows<n0).sum())
    center=X[:n_fit].mean(axis=0);scale=X[:n_fit].std(axis=0);center[0]=0;scale[0]=1
    Z=(X-center)/scale
    xtx=Z[:n_fit].T@Z[:n_fit];xty=Z[:n_fit].T@y[:n_fit]
    forecasts=[]
    for i in range(n_fit,len(y)):
        beta=linalg.solve(xtx,xty,assume_a='pos',check_finite=False)
        f=float(Z[i]@beta)
        if i in [n_fit,len(y)-1]:
            qr=linalg.lstsq(X[:i],y[:i],lapack_driver='gelsy')[0]
            error=abs(f-float(X[i]@qr));max_check=max(max_check,error);assert error<1e-8
        forecasts.append(f)
        xtx+=np.outer(Z[i],Z[i]);xty+=Z[i]*y[i]
    return np.array(forecasts)

def acf(u,lag):
    u=np.asarray(u)-np.mean(u)
    return float(u[lag:]@u[:-lag]/(u@u)) if lag else 1.

def root(b,K,p):
    blocks=[b[1+j*K:1+(j+1)*K].T for j in range(p)]
    companion=np.zeros((K*p,K*p));companion[:K,:]=np.hstack(blocks)
    if p>1:companion[K:,:-K]=np.eye(K*(p-1))
    return float(np.max(np.abs(np.linalg.eigvals(companion))))

for case,p in [('BIC',p_main),('AIC',p_aic)]:
    f=pd.DataFrame({'date':data.date.iloc[n0:].to_numpy(),'actual':data.ES.iloc[n0:].to_numpy()})
    for label,cols in markets.items():
        f[label]=forecast(data,cols,p)
        X,Y,_=design(data.iloc[:n0],cols,p)
        b,u=fit(X,Y);e=u[:,0];T=len(e)
        # Breusch-Godfrey auxiliary regression on 20 residual lags and original X.
        h=20
        aux=np.column_stack([X[h:]]+[e[h-j:T-j] for j in range(1,h+1)])
        _,v=fit(aux,e[h:])
        R2=1-float(v@v)/float(np.sum((e[h:]-e[h:].mean())**2))
        bg=(T-h)*R2
        diagnostics.append(dict(case=case,model=label,p=p,n=T,parameters_per_equation=X.shape[1],
            max_root=root(b,len(cols),p),residual_acf1=acf(e,1),residual_acf5=acf(e,5),
            residual_acf20=acf(e,20),BG20=bg,BG20_p=stats.chi2.sf(bg,20)))
        if label=='Full VAR':
            pd.DataFrame({'lag':np.arange(1,41),'ACF':[acf(e,j) for j in range(1,41)]}).to_csv(OUT/f'residual_acf_{case}.csv',index=False)
        if label!='AR':
            keep=[0]+[1+j*len(cols) for j in range(p)]+list(range(1+p*len(cols),X.shape[1]))
            _,r=fit(X[:,keep],Y[:,0]);q=(len(cols)-1)*p
            ssr0=r@r;ssr1=e@e;F=((ssr0-ssr1)/q)/(ssr1/(T-X.shape[1]))
            granger.append(dict(case=case,model=label,p=p,F=F,q=q,df_resid=T-X.shape[1],p_value=stats.f.sf(F,q,T-X.shape[1])))
    f['Persistence']=data.ES.iloc[n0-1:-1].to_numpy()
    for label in list(markets)+['Persistence']:
        e=f.actual-f[label];mse=float(np.mean(e**2));ar_mse=float(np.mean((f.actual-f.AR)**2))
        all_accuracy.append(dict(case=case,model=label,p=p,n=len(f),MSE=mse,RMSE=np.sqrt(mse),MAE=float(np.mean(np.abs(e))),gain_vs_AR_pct=100*(1-mse/ar_mse)))
    f.to_csv(OUT/f'forecasts_{case}.csv',index=False)

# A simple timing sensitivity: one additional retained-observation Treasury lag.
# Retain identical target dates and one common training start for AR/full pairs.
timing=data.copy();timing['TY']=timing.TY.shift(1)
timing_scores=[]
for label in ['AR','Gas and Treasury','Full VAR']:
    pred=forecast(timing,markets[label],p_main,start=p_main+1);e=data.ES.iloc[n0:].to_numpy()-pred
    timing_scores.append(dict(model=label,MSE=np.mean(e**2),MAE=np.mean(abs(e))))
pd.DataFrame(timing_scores).to_csv(OUT/'treasury_timing_sensitivity.csv',index=False)

# Course-level robustness: first differences, then reconstruct log-RV5 forecasts.
dif=data.copy();dif[names]=dif[names].diff()
dif_ic=[]
for p in range(1,21):
    X,Y,_=design(dif.iloc[:n0],names,p,start=21)
    b,u=fit(X,Y);T=len(Y);K=len(names);k=X.shape[1]
    ld=np.linalg.slogdet(u.T@u/T)[1]
    dif_ic.append(dict(p=p,AIC=ld+2*K*k/T,BIC=ld+np.log(T)*K*k/T))
dif_ic=pd.DataFrame(dif_ic);p_diff=int(dif_ic.loc[dif_ic.BIC.idxmin(),'p'])
dif_ic.to_csv(OUT/'differenced_lag_selection.csv',index=False)
dif_scores=[]
for label in ['AR','Full VAR']:
    pred=forecast(dif,markets[label],p_diff,start=p_diff+1)+data.ES.iloc[n0-1:-1].to_numpy()
    e=data.ES.iloc[n0:].to_numpy()-pred
    dif_scores.append(dict(model=label,p=p_diff,n=len(e),MSE=np.mean(e**2),MAE=np.mean(abs(e))))
pd.DataFrame(dif_scores).to_csv(OUT/'differenced_sensitivity.csv',index=False)

stationarity=[]; summary=[]
for v in names:
    y=data[v].iloc[:n0].to_numpy();dy=np.diff(y);r=np.arange(20,len(dy))
    # ADF with intercept, 20 lagged differences, no deterministic trend.
    X=np.column_stack([np.ones(len(r)),y[r]]+[dy[r-j] for j in range(1,21)])
    b,u=fit(X,dy[r]);s2=u@u/(len(u)-X.shape[1]);se=np.sqrt(s2*np.linalg.inv(X.T@X)[1,1])
    adf=float(b[1]/se)
    # Level KPSS with Bartlett long-run variance, 28 lags.
    u=y-y.mean();L=28;n=len(y)
    omega=u@u/n+sum(2*(1-j/(L+1))*float(u[j:]@u[:-j])/n for j in range(1,L+1))
    kpss=float(np.sum(np.cumsum(u)**2)/(n*n*omega))
    stationarity.append(dict(variable=v,ADF=adf,ADF_lags=20,ADF_5pct=-2.86,ADF_reject=adf<-2.86,
                             KPSS=kpss,KPSS_lags=28,KPSS_5pct=.463,KPSS_reject=kpss>.463))
    summary.append(dict(variable=v,n=n,mean=y.mean(),std=y.std(ddof=1),min=y.min(),max=y.max(),ACF1=acf(y,1),ACF20=acf(y,20)))
monthly=[]
for v in names[:-1]:
    lev=df['rv5_'+v].iloc[:n0]
    means=lev.groupby(df.date.iloc[:n0].dt.month).mean()
    for m,val in means.items():monthly.append(dict(variable=v,month=int(m),mean_RV5=float(val),relative_to_overall=float(val/lev.mean())))

accuracy=pd.DataFrame(all_accuracy);accuracy.to_csv(OUT/'accuracy.csv',index=False)
pd.DataFrame(diagnostics).to_csv(OUT/'diagnostics.csv',index=False)
pd.DataFrame(granger).to_csv(OUT/'granger_tests.csv',index=False)
pd.DataFrame(stationarity).to_csv(OUT/'stationarity.csv',index=False)
pd.DataFrame(summary).to_csv(OUT/'descriptive_statistics_training.csv',index=False)
pd.DataFrame(monthly).to_csv(OUT/'seasonality_training.csv',index=False)
data.assign(split=np.where(np.arange(len(data))<n0,'initial_training','test')).to_csv(OUT/'analysis_data.csv',index=False)
metadata=dict(n=len(data),initial_training=n0,test=len(data)-n0,start=str(data.date.iloc[0].date()),
    end=str(data.date.iloc[-1].date()),train_end=str(cutoff.date()),test_start=str(data.date.iloc[n0].date()),
    p_BIC=p_main,p_AIC=p_aic,models=markets,input_sha256=hashlib.sha256(DATA.read_bytes()).hexdigest(),
    maximum_QR_forecast_check_difference=max_check,treasury_zero_count=int((df.rv_yield_10==0).sum()),
    ADF_critical_value_note='Large-sample 5% intercept-only Dickey-Fuller value, rounded to -2.86',
    numerical_engine='Python scipy/numpy OLS; R companion supplied separately')
(OUT/'metadata.json').write_text(json.dumps(metadata,indent=2))
print(accuracy.to_string(index=False))
print('DIAGNOSTICS\n',pd.DataFrame(diagnostics).to_string(index=False))
print('GRANGER\n',pd.DataFrame(granger).to_string(index=False))
print('STATIONARITY\n',pd.DataFrame(stationarity).to_string(index=False))
print('TIMING\n',pd.DataFrame(timing_scores).to_string(index=False))
print('QR CHECK',max_check)
