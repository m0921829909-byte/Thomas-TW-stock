import streamlit as st
from pathlib import Path
import pandas as pd, subprocess, sys

st.set_page_config(page_title="台股盤後選股器",page_icon="📈",layout="wide")
st.title("📈 台股盤後選股器")
st.caption("Yahoo Finance｜手機版｜每日盤後自動保存結果")

R=Path("results"); R.mkdir(exist_ok=True)
files=sorted(R.glob("*.csv"))
if files:
    f=files[-1]; df=pd.read_csv(f)
    st.success(f"最新結果：{f.stem}｜符合 {len(df)} 檔")
    st.dataframe(df,use_container_width=True,hide_index=True)
    st.download_button("⬇️ 下載 CSV",df.to_csv(index=False).encode("utf-8-sig"),file_name=f.name,mime="text/csv",use_container_width=True)
else:
    st.info("尚無結果；第一次可按下方按鈕執行。")

if st.button("🚀 立即重新選股",type="primary",use_container_width=True):
    with st.spinner("正在抓取 Yahoo Finance…"):
        r=subprocess.run([sys.executable,"screener.py"],capture_output=True,text=True)
    if r.returncode==0: st.rerun()
    st.error(r.stderr[-3000:])

st.divider()
st.markdown("**固定條件：** 漲幅3～5%、量比≥1、換手率5～10%、市值100～1000億、VOL5>VOL10>VOL20、今日量>VOL5、收盤>VWAP。")
st.caption("僅供研究與選股參考，不構成投資建議。")
