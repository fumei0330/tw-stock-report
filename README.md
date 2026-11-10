# 台灣股市三大法人報告 Web App

台灣股市收盤後三大法人（外資、投信、自營商）買賣超報告，含自選股追蹤。  
資料來源：台灣證券交易所 (TWSE) 開放 API，**完全免費**。

## 功能
- 🌍 外資買超 / 賣超 Top 20
- 📦 投信買超 Top 20
- 🏆 三大法人合計買超 Top 20
- ⭐ 自選股追蹤（收盤價、漲跌幅、三大法人動向）
- 📱 手機瀏覽器友善介面

## 本機執行

```bash
pip install -r requirements.txt
python app.py
# 開啟 http://localhost:5000
```

## 雲端部署（Render）

詳見 [DEPLOY.md](DEPLOY.md)

## 自選股設定

修改 `app.py` 中的 `DEFAULT_WATCHLIST`，或在 Render 環境變數 `WATCHLIST` 設定 JSON：

```json
[{"code":"2330","name":"台積電"},{"code":"2454","name":"聯發科"}]
```
