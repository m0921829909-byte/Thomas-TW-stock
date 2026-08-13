import time
from pathlib import Path
from datetime import datetime
import pandas as pd, numpy as np, requests, yfinance as yf

OUT=Path("results"); OUT.mkdir(exist_ok=True)
H={"User-Agent":"Mozilla/5.0"}

def get(u):
    r=requests.get(u,headers=H,timeout=30); r.raise_for_status(); return r.json()

def universe():
    tw=pd.DataFrame(get("https://openapi.twse.com.tw/v1/opendata/t187ap03_L"))
    def col(d,words): return next(c for c in d.columns if any(w in c for w in words))
    tw=tw[[col(tw,["公司代號","Code"]),col(tw,["公司名稱","Name"])]]
    tw.columns=["symbol","name"]; tw["market"]="TW"
    d=None
    for u in ["https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O","https://www.tpex.org.tw/openapi/v1/t187ap03_O"]:
        try:
            x=pd.DataFrame(get(u))
            if x.empty: continue
            x=x[[col(x,["代號","Code","公司代號"]),col(x,["名稱","Name","公司名稱"])]]
            x.columns=["symbol","name"]; x["market"]="TWO"; d=x; break
        except Exception: pass
    if d is None: raise RuntimeError("TPEx 股票清單暫時無法取得")
    u=pd.concat([tw,d],ignore_index=True); u["symbol"]=u.symbol.astype(str).str.strip()
    return u[u.symbol.str.fullmatch(r"\d{4,6}")].drop_duplicates(["symbol","market"])

def flat(x):
    if x is None or x.empty:return pd.DataFrame()
    if isinstance(x.columns,pd.MultiIndex):x.columns=x.columns.get_level_values(0)
    return x.dropna(subset=["Close","Volume"])

def one(r):
    s=r.symbol+(".TW" if r.market=="TW" else ".TWO")
    d=flat(yf.download(s,period="3mo",interval="1d",auto_adjust=False,progress=False,threads=False))
    if len(d)<25:return
    c=float(d.Close.iloc[-1]); p=float(d.Close.iloc[-2]); v=float(d.Volume.iloc[-1]); g=(c/p-1)*100
    if not 3<=g<=5:return
    a,b,e=[float(d.Volume.tail(n).mean()) for n in (5,10,20)]
    if not(a>b>e and v>a):return
    try:i=yf.Ticker(s).get_info()
    except:i={}
    cap=i.get("marketCap"); sh=i.get("sharesOutstanding") or i.get("impliedSharesOutstanding"); av=i.get("averageDailyVolume3Month")
    if not(cap and sh and av):return
    capb=cap/1e8; turn=v/sh*100; ratio=v/av
    if not(1<=ratio and 5<=turn<=10 and 100<=capb<=1000):return
    try:
        m=flat(yf.download(s,period="1d",interval="1m",auto_adjust=False,progress=False,threads=False,prepost=False))
        if m.empty or m.Volume.sum()==0:return
        tp=(m.High+m.Low+m.Close)/3; vw=float((tp*m.Volume).sum()/m.Volume.sum())
    except:return
    if c<=vw:return
    gap=(c/vw-1)*100
    score=min(20,max(0,(g-3)/2*20))+min(20,max(0,(ratio-1)/2*20))+max(0,15-abs(turn-7.5)/2.5*15)+20+min(15,max(0,gap/3*15))+max(0,10-abs(capb-550)/550*10)
    return {"代號":r.symbol,"名稱":r["name"],"漲幅%":round(g,2),"量比*":round(ratio,2),"換手率%":round(turn,2),"市值億":round(capb,1),"VOL5":int(a),"VOL10":int(b),"VOL20":int(e),"VWAP":round(vw,2),"收盤":round(c,2),"收盤高於VWAP%":round(gap,2),"分數":round(score,1)}

u=universe(); rows=[]
for _,r in u.iterrows():
    try:
        x=one(r)
        if x: rows.append(x)
    except Exception: pass
    time.sleep(.1)
out=pd.DataFrame(rows)
if not out.empty:
    out=out.sort_values("分數",ascending=False).reset_index(drop=True); out.insert(0,"排名",range(1,len(out)+1))
out.to_csv(OUT/f"{datetime.now():%Y-%m-%d}.csv",index=False,encoding="utf-8-sig")
print("完成",len(out))
