import streamlit as st
from pathlib import Path
import pandas as pd

st.set_page_config(page_title="台股盤後選股器", page_icon="📈", layout="wide")
st.title("📈 台股盤後選股器 v5.1")
st.caption("Yahoo Finance｜手機版｜盤後自動保存結果")

RESULTS = Path("results")
RESULTS.mkdir(exist_ok=True)

def load_latest():
    good = []
    for f in RESULTS.glob("*.csv"):
        try:
            if f.stat().st_size == 0:
                continue
            df = pd.read_csv(f)
            good.append((f, df))
        except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError):
            continue
    if not good:
        return None, None
    good.sort(key=lambda x: x[0].name)
    return good[-1]

f, df = load_latest()
if f is not None:
    st.success(f"最新結果：{f.stem}｜符合 {len(df)} 檔")
    if df.empty:
        st.info("今天沒有股票通過全部條件。")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("⬇️ 下載今日結果", df.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f.name, mime="text/csv", use_container_width=True)
else:
    st.info("目前沒有有效的選股結果。請到 GitHub → Actions → Daily Taiwan Stock Screener → Run workflow。")

st.divider()
st.subheader("📌 選股條件")
st.write("漲幅 3～5%｜量比 ≥ 1｜換手率 5～10%｜市值 100～1000 億｜VOL5>VOL10>VOL20｜今日量>VOL5｜收盤>VWAP")
st.caption("本版已修正空白/損壞 CSV 不會再造成 pandas EmptyDataError。")
