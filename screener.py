import time
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
import requests
import yfinance as yf

OUT = Path("results")
OUT.mkdir(exist_ok=True)
H = {"User-Agent": "Mozilla/5.0"}

def get_json(url):
    r = requests.get(url, headers=H, timeout=30)
    r.raise_for_status()
    return r.json()

def find_col(df, words):
    return next(c for c in df.columns if any(w in str(c) for w in words))

def universe():
    tw = pd.DataFrame(get_json("https://openapi.twse.com.tw/v1/opendata/t187ap03_L"))
    tw = tw[[find_col(tw, ["公司代號","Code"]), find_col(tw, ["公司名稱","Name"])]]
    tw.columns = ["symbol","name"]
    tw["market"] = "TW"
    tp = None
    for url in ["https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O",
                "https://www.tpex.org.tw/openapi/v1/t187ap03_O"]:
        try:
            x = pd.DataFrame(get_json(url))
            if x.empty:
                continue
            x = x[[find_col(x, ["代號","Code","公司代號"]),
                   find_col(x, ["名稱","Name","公司名稱"])]]
            x.columns = ["symbol","name"]
            x["market"] = "TWO"
            tp = x
            break
        except Exception:
            pass
    if tp is None:
        raise RuntimeError("TPEx 股票清單暫時無法取得")
    u = pd.concat([tw,tp], ignore_index=True)
    u["symbol"] = u["symbol"].astype(str).str.strip()
    return u[u.symbol.str.fullmatch(r"\d{4,6}")].drop_duplicates(["symbol","market"]).reset_index(drop=True)

def ys(code, market):
    return code + (".TW" if market == "TW" else ".TWO")

def flat(x):
    if x is None or x.empty:
        return pd.DataFrame()
    if isinstance(x.columns, pd.MultiIndex):
        x.columns = x.columns.get_level_values(0)
    return x.dropna(subset=["Close","Volume"])

def main():
    u = universe()
    symbols = [ys(str(a),b) for a,b in zip(u.symbol,u.market)]
    candidates = []
    for start in range(0, len(symbols), 80):
        batch = symbols[start:start+80]
        try:
            d = yf.download(batch, period="3mo", interval="1d", auto_adjust=False,
                             progress=False, threads=True, group_by="ticker")
        except Exception:
            continue
        if d is None or d.empty or not isinstance(d.columns, pd.MultiIndex):
            continue
        for s in d.columns.get_level_values(0).unique():
            try:
                x = flat(d[s])
                if len(x) < 25:
                    continue
                close = float(x.Close.iloc[-1])
                prev = float(x.Close.iloc[-2])
                vol = float(x.Volume.iloc[-1])
                gain = (close/prev - 1) * 100
                v5 = float(x.Volume.tail(5).mean())
                v10 = float(x.Volume.tail(10).mean())
                v20 = float(x.Volume.tail(20).mean())
                avg = float(x.Volume.mean())
                ratio = vol/avg if avg > 0 else 0
                if 3 <= gain <= 5 and ratio >= 1 and v5 > v10 > v20 and vol > v5:
                    candidates.append((s,close,vol,gain,v5,v10,v20,ratio))
            except Exception:
                pass

    if candidates:
        cdf = pd.DataFrame(candidates, columns=["ysym","close","volume","gain","vol5","vol10","vol20","ratio"])
        um = u.copy()
        um["ysym"] = [ys(str(a),b) for a,b in zip(um.symbol,um.market)]
        cdf = cdf.merge(um,on="ysym",how="left")
        rows = []
        for _, r in cdf.iterrows():
            try:
                info = yf.Ticker(r.ysym).get_info()
                cap = info.get("marketCap")
                shares = info.get("sharesOutstanding") or info.get("impliedSharesOutstanding")
                if not (cap and shares):
                    continue
                capb = cap/1e8
                turnover = r.volume/shares*100
                if not (100 <= capb <= 1000 and 5 <= turnover <= 10):
                    continue
                m = flat(yf.download(r.ysym, period="1d", interval="1m",
                                     auto_adjust=False, progress=False,
                                     threads=False, prepost=False))
                if m.empty or m.Volume.sum() == 0:
                    continue
                tp = (m.High+m.Low+m.Close)/3
                vwap = float((tp*m.Volume).sum()/m.Volume.sum())
                if r.close <= vwap:
                    continue
                gap = (r.close/vwap-1)*100
                score = (min(20,max(0,(r.gain-3)/2*20))
                         + min(20,max(0,(r.ratio-1)/2*20))
                         + max(0,15-abs(turnover-7.5)/2.5*15)
                         + 20 + min(15,max(0,gap/3*15))
                         + max(0,10-abs(capb-550)/550*10))
                rows.append({"代號":r.symbol,"名稱":r["name"],"漲幅%":round(r.gain,2),
                             "量比*":round(r.ratio,2),"換手率%":round(turnover,2),
                             "市值億":round(capb,1),"VOL5":int(r.vol5),
                             "VOL10":int(r.vol10),"VOL20":int(r.vol20),
                             "VWAP":round(vwap,2),"收盤":round(r.close,2),
                             "收盤高於VWAP%":round(gap,2),"分數":round(score,1)})
            except Exception:
                continue
        out = pd.DataFrame(rows)
    else:
        out = pd.DataFrame()

    if not out.empty:
        out = out.sort_values("分數",ascending=False).reset_index(drop=True)
        out.insert(0,"排名",range(1,len(out)+1))
    else:
        out = pd.DataFrame(columns=["排名","代號","名稱","漲幅%","量比*","換手率%","市值億",
                                    "VOL5","VOL10","VOL20","VWAP","收盤","收盤高於VWAP%","分數"])

    final = OUT / f"{datetime.now():%Y-%m-%d}.csv"
    temp = OUT / f".{datetime.now():%Y-%m-%d}.tmp.csv"
    out.to_csv(temp,index=False,encoding="utf-8-sig")
    temp.replace(final)
    print("完成：",len(out),"檔")

if __name__ == "__main__":
    main()
