import pandas as pd, numpy as np, json, warnings, os
warnings.filterwarnings("ignore")
import geopandas as gpd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from statsmodels.tsa.holtwinters import ExponentialSmoothing, SimpleExpSmoothing
from statsmodels.tsa.arima.model import ARIMA

from pathlib import Path
BASE = Path(__file__).resolve().parent          # the Waste_pipeline folder
IN  = str(BASE / "Data") + "/"                  # inputs
OUT = str(BASE / "Output") + "/"                # results
os.makedirs(OUT, exist_ok=True)
SITES=['OLUSHOSUN','SOLOUS','BADAGRY','EPE','IKORODU']
MM={m:i for i,m in enumerate(['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'],1)}

# =============== A. LAGOS: clean ===============
raw=pd.read_excel(IN+"lagos_waste_data.xlsx")
raw['date']=pd.to_datetime(dict(year=raw.Year,month=raw.Month.str.strip().str.upper().map(MM),day=1))
raw=raw.sort_values('date').reset_index(drop=True)
clean=raw.copy(); flags=[]
for s in SITES:
    tpt=raw[f'{s} TONNAGE']/raw[f'{s} TRIPS']; med=tpt.median(); mad=(tpt-med).abs().median()
    bad=(tpt-med).abs()>max(5*1.4826*mad,0.25*med)
    for i in raw.index[bad]:
        new=int(round(raw.loc[i,f'{s} TRIPS']*med))
        flags.append(dict(Date=raw.loc[i,'date'].strftime('%Y-%m'),Site=s,Field='Tonnage',Original=int(raw.loc[i,f'{s} TONNAGE']),
                          Corrected=new,Rule=f'Tonnes/trip {tpt[i]:.2f} vs site median {med:.2f}; replaced with trips x median'))
        clean.loc[i,f'{s} TONNAGE']=new
flags=pd.DataFrame(flags)
clean['total']=clean[[f'{s} TONNAGE' for s in SITES]].sum(axis=1)
y=clean.set_index('date')['total'].astype(float)
spike=pd.Timestamp('2023-06-01')
y_model=y.copy(); y_model[spike]=(y[spike-pd.DateOffset(months=1)]+y[spike+pd.DateOffset(months=1)])/2
sol=clean.set_index('date')['SOLOUS TRIPS']; pre=sol[:'2023-05-01'].mean(); post=sol['2023-07-01':].mean()

# =============== B. LAGOS: backtest + forecast ===============
def f_naive(tr,h): return np.repeat(tr[-1],h)
def f_mean6(tr,h): return np.repeat(tr[-6:].mean(),h)
def f_snaive(tr,h): return np.array([tr[-12+(i%12)] for i in range(h)])
def f_ses(tr,h): return SimpleExpSmoothing(tr,initialization_method='estimated').fit().forecast(h)
def f_damped(tr,h): return ExponentialSmoothing(tr,trend='add',damped_trend=True,initialization_method='estimated').fit().forecast(h)
def f_arima(tr,h): return ARIMA(tr,order=(0,1,1),trend='t').fit().forecast(h)
def f_lin12(tr,h):
    b=np.polyfit(np.arange(12),tr[-12:],1); return np.maximum(np.polyval(b,np.arange(12,12+h)),0)
MODELS={'Naive (last value)':f_naive,'Mean of last 6 months':f_mean6,'Seasonal naive (t-12)':f_snaive,'Simple exp. smoothing':f_ses,
        'Damped-trend ETS':f_damped,'ARIMA(0,1,1)+drift':f_arima,'Linear trend (last 12m)':f_lin12}
v=y_model.values; H=6; rows=[]
for T in range(24,31):
    for name,f in MODELS.items():
        fc=np.asarray(f(v[:T],H))
        for h in range(H): rows.append(dict(Model=name,Train_end=y_model.index[T-1].strftime('%Y-%m'),Horizon=h+1,Actual=v[T+h],Forecast=float(fc[h])))
bt=pd.DataFrame(rows); bt['Error']=bt.Forecast-bt.Actual; bt['APE']=bt.Error.abs()/bt.Actual*100
def summ(g): return pd.Series(dict(MAE=g.Error.abs().mean(),RMSE=np.sqrt((g.Error**2).mean()),MAPE=g.APE.mean(),Bias=g.Error.mean()))
metrics=bt.groupby('Model').apply(summ)
metrics['MAPE_h1_3']=bt[bt.Horizon<=3].groupby('Model').APE.mean(); metrics['MAPE_h4_6']=bt[bt.Horizon>=4].groupby('Model').APE.mean()
metrics=metrics.sort_values('MAPE').reset_index()

FH=24; fdates=pd.date_range('2025-01-01',periods=FH,freq='MS')
fc=pd.DataFrame({'Date':fdates})
for n in ['Linear trend (last 12m)','ARIMA(0,1,1)+drift','Damped-trend ETS','Simple exp. smoothing']:
    fc[n]=np.asarray(MODELS[n](v,FH))

# =============== C. STATES: clean + GIS join ===============
st=pd.read_excel(IN+"State Level OFMSW Amounts Generated - Nigeria.xlsx")
st=st.iloc[:,:7]; st.columns=['State','Per_capita_kg_day','Pop_2006','OFMSW_pct','Pop_2023','MSW_t_yr_file','OFMSW_t_yr_file']
st=st[st.State!='Federal Republic of Nigeria'].copy()
st['State']=st.State.replace({'FCT':'Federal Capital Territory'})
ZONE={'North Central':['Benue','Kogi','Kwara','Nasarawa','Niger','Plateau','Federal Capital Territory'],
 'North East':['Adamawa','Bauchi','Borno','Gombe','Taraba','Yobe'],'North West':['Jigawa','Kaduna','Kano','Katsina','Kebbi','Sokoto','Zamfara'],
 'South East':['Abia','Anambra','Ebonyi','Enugu','Imo'],'South South':['Akwa Ibom','Bayelsa','Cross River','Delta','Edo','Rivers'],
 'South West':['Ekiti','Lagos','Ogun','Ondo','Osun','Oyo']}
z={s:k for k,v_ in ZONE.items() for s in v_}; st['Zone']=st.State.map(z); assert st.Zone.notna().all()
gj=json.load(open(IN+"nigeria_state_boundaries.geojson.txt"))
g=gpd.GeoDataFrame.from_features(gj['features'],crs="EPSG:4326")
g['Area_km2']=g.to_crs(6933).area/1e6
g=g.rename(columns={'admin1Name':'State'})[['State','admin1Pcod','Area_km2','geometry']]
st=st.merge(g[['State','admin1Pcod','Area_km2']],on='State',how='left'); assert st.Area_km2.notna().all()
st['MSW_t_yr']=st.Per_capita_kg_day*st.Pop_2023*365/1000
st['OFMSW_t_yr']=st.MSW_t_yr*st.OFMSW_pct/100
st['Density']=st.Pop_2023/st.Area_km2
st['Share_national']=st.MSW_t_yr/st.MSW_t_yr.sum()
gm=g.merge(st.drop(columns=['Area_km2','admin1Pcod']),on='State')
gm.to_file(OUT+"nigeria_states_waste.geojson",driver="GeoJSON")

# =============== D. figures ===============
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9})
fig,ax=plt.subplots(2,1,figsize=(11,9),gridspec_kw={'height_ratios':[1.5,1]})
a=ax[0]
a.plot(y.index,y/1e3,color='#1F4E78',lw=2,label='Dumpsite receipts, all 5 sites (cleaned)')
a.scatter([spike],[271794/1e3],color='#C00000',zorder=5,s=28); a.annotate('Raw Jun-2023 value\n(Olushosun entry error)',(spike,271.8),xytext=(-150,-6),textcoords='offset points',color='#C00000',fontsize=8)
a.scatter([spike],[y[spike]/1e3],color='#1F4E78',zorder=5,s=28)
low=fc['Damped-trend ETS']; cen=fc[['Linear trend (last 12m)','ARIMA(0,1,1)+drift','Damped-trend ETS']].mean(axis=1); high=fc['Simple exp. smoothing']
a.fill_between(fc.Date,low/1e3,high/1e3,color='#F4B183',alpha=.45,label='Scenario range (steep decline to stabilisation)')
a.plot(fc.Date,cen/1e3,color='#C55A11',lw=2,ls='--',label='Central (mean of 3 trend models)')
a.axvline(pd.Timestamp('2025-01-01'),color='grey',lw=.8,ls=':'); a.axvline(pd.Timestamp('2023-07-01'),color='grey',lw=.8,ls=':')
a.text(pd.Timestamp('2023-07-15'),12,'Jul-2023: Solous trips fall ~50%',fontsize=8,color='dimgrey')
a.set_ylim(0,300); a.set_ylabel('Thousand tonnes / month'); a.set_title('Lagos dumpsite receipts: history and 2025-2026 scenarios (receipts are not generation)',loc='left',fontweight='bold')
a.legend(loc='upper right',frameon=False,fontsize=8); a.grid(alpha=.25)
b=ax[1]; cols=['#1F4E78','#2E75B6','#9DC3E6','#A9D18E','#FFD966']
b.stackplot(clean.date,*[clean[f'{s} TONNAGE']/1e3 for s in SITES],labels=[s.title() for s in SITES],colors=cols)
b.set_ylabel('Thousand tonnes / month'); b.set_title('Contribution by dumpsite (cleaned)',loc='left',fontweight='bold'); b.legend(ncol=5,loc='upper right',frameon=False,fontsize=8); b.grid(alpha=.25)
import matplotlib.dates as mdates
for q in ax: q.xaxis.set_major_locator(mdates.YearLocator()); q.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
plt.tight_layout(); plt.savefig(OUT+"lagos_forecast.png",dpi=150); plt.close()

fig,axs=plt.subplots(2,2,figsize=(13,10))
def cmap(a_,col,title,cm,fmt,scale=1,lab=True):
    gm.plot(column=col,ax=a_,cmap=cm,edgecolor='white',linewidth=.6,legend=True,legend_kwds={'shrink':.55,'format':fmt})
    a_.set_title(title,fontweight='bold',loc='left'); a_.axis('off')
    if lab:
        for _,r in gm.nlargest(5,col).iterrows():
            p=r.geometry.representative_point()
            if r.State=='Lagos': a_.annotate('Lagos',(p.x,p.y),xytext=(-6,-22),textcoords='offset points',ha='center',fontsize=7,fontweight='bold',arrowprops=dict(arrowstyle='-',lw=.6))
            else: a_.annotate(r.State,(p.x,p.y),ha='center',fontsize=7,fontweight='bold')
gm['MSW_Mt']=gm.MSW_t_yr/1e6; gm['OFMSW_Mt']=gm.OFMSW_t_yr/1e6
cmap(axs[0,0],'MSW_Mt','MSW generated, 2023 (million tonnes/yr)','YlOrRd','%.1f')
cmap(axs[0,1],'Per_capita_kg_day','Per capita MSW (kg/person/day)','PuBu','%.2f')
cmap(axs[1,0],'OFMSW_pct','Organic fraction of MSW (%)','Greens','%.0f',lab=False)
cmap(axs[1,1],'OFMSW_Mt','Organic waste generated (million tonnes/yr)','YlGn','%.1f')
fig.suptitle('Nigeria state-level waste (derived: per capita rate x 2023 population)',fontsize=12,fontweight='bold',x=.02,ha='left')
plt.tight_layout(); plt.savefig(OUT+"nigeria_state_waste_map.png",dpi=130); plt.close()

# =============== E. console summary for the write-up ===============
top5=st.nlargest(5,'MSW_t_yr'); 
summary=dict(
 solous_pre=pre,solous_post=post,
 annual_receipts={int(k):float(x) for k,x in y.groupby(y.index.year).sum().items()},
 fc_year={'low':{2025:low[:12].sum(),2026:low[12:].sum()},'central':{2025:cen[:12].sum(),2026:cen[12:].sum()},'high':{2025:high[:12].sum(),2026:high[12:].sum()}},
 top5=top5[['State','MSW_t_yr','Share_national']].to_dict('records'),top5_share=float(top5.Share_national.sum()),
 zone=st.groupby('Zone').apply(lambda d: pd.Series(dict(pop=d.Pop_2023.sum(),msw=d.MSW_t_yr.sum(),pc=d.MSW_t_yr.sum()*1000/(d.Pop_2023.sum()*365),of=d.OFMSW_t_yr.sum()/d.MSW_t_yr.sum()))).round(3).to_dict('index'),
 tot=dict(pop=st.Pop_2023.sum(),msw=st.MSW_t_yr.sum(),of=st.OFMSW_t_yr.sum()),
 maxdiff=float((st.MSW_t_yr-st.MSW_t_yr_file).abs().max()))
print(json.dumps(summary,indent=1,default=float))
print(metrics.round(1).to_string())
