# Yahoo 台股盤後選股器 v4

## 部署
1. GitHub 建立 Public repository，例如 `yahoo-tw-stock-screener`。
2. 上傳本資料夾內所有檔案與 `.github/workflows/daily_screener.yml`。
3. 開啟 https://share.streamlit.io/，用 GitHub 登入並授權。
4. Create app → Repository 選你的 repo → Branch `main` → Main file `app.py` → Deploy。
5. 完成後得到 `*.streamlit.app` 網址，iPhone Safari 開啟即可。
6. GitHub Actions 每週一至週五台灣時間約17:30自動執行；也可 Actions → Daily Taiwan Stock Screener → Run workflow 手動執行。

## 條件
漲幅3～5%、量比≥1、換手率5～10%、市值100～1000億、VOL5>VOL10>VOL20、今日量>VOL5、收盤>VWAP。

注意：Yahoo 免費資料的量比、流通股數與1分鐘資料可能缺失；缺資料會排除。
