#!/usr/bin/env python3
"""
台灣股市三大法人報告 - Web App
資料來源：台灣證券交易所 (TWSE)
"""

import requests
import json
import os
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify, request, redirect, url_for

app = Flask(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.twse.com.tw/",
}

# 自選股（雲端用環境變數或預設值）
DEFAULT_WATCHLIST = [
    {"code": "2330", "name": "台積電"},
    {"code": "2317", "name": "鴻海"},
    {"code": "2454", "name": "聯發科"},
    {"code": "2308", "name": "台達電"},
    {"code": "2881", "name": "富邦金"},
]

def get_watchlist():
    raw = os.environ.get("WATCHLIST", "")
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            pass
    return DEFAULT_WATCHLIST

def to_int(s):
    try:
        return int(str(s).replace(",", "").strip())
    except:
        return 0

def fmt_shares(n):
    if abs(n) >= 100_000_000:
        return f"{n/100_000_000:+.2f} 億"
    elif abs(n) >= 10_000:
        return f"{n/10_000:+.1f} 萬"
    else:
        return f"{n:+,}"

def find_latest_trading_date():
    today = datetime.now()
    for i in range(10):
        d = today - timedelta(days=i)
        if d.weekday() >= 5:
            continue
        date_str = d.strftime("%Y%m%d")
        try:
            url = f"https://www.twse.com.tw/fund/T86?response=json&date={date_str}&selectType=ALLBUT0999"
            r = requests.get(url, headers=HEADERS, timeout=10)
            data = r.json()
            if data.get("total", 0) > 0:
                return date_str
        except:
            continue
    return None

def fetch_institutional(date_str):
    url = f"https://www.twse.com.tw/fund/T86?response=json&date={date_str}&selectType=ALLBUT0999"
    r = requests.get(url, headers=HEADERS, timeout=15)
    data = r.json()
    if data.get("stat") != "OK" or not data.get("data"):
        return []
    results = []
    for row in data["data"]:
        results.append({
            "code":        row[0].strip(),
            "name":        row[1].strip(),
            "foreign_net": to_int(row[4]),
            "trust_net":   to_int(row[10]),
            "dealer_net":  to_int(row[11]),
            "total_net":   to_int(row[18]),
        })
    return results

def fetch_stock_price(code, date_str):
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date_str}&stockNo={code}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        data = r.json()
        if data.get("stat") != "OK" or not data.get("data"):
            return None
        last = data["data"][-1]
        try:
            close_val  = float(last[6].replace(",", ""))
            change_val = float(last[7].replace(",", "").replace("+","").replace("▲","").replace("▼","-").replace("X","0"))
            prev_close = close_val - change_val
            change_pct = f"{change_val/prev_close*100:+.2f}" if prev_close != 0 else "0.00"
        except:
            change_pct = "N/A"
        try:
            volume_lots = f"{int(last[1].replace(',','')) // 1000:,}"
        except:
            volume_lots = last[1]
        return {
            "open": last[3], "high": last[4], "low": last[5],
            "close": last[6], "change": last[7],
            "change_pct": change_pct, "volume": volume_lots,
        }
    except:
        return None

# ── HTML 模板 ─────────────────────────────────────────────────────

HTML = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>台灣股市三大法人報告</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
<style>
  body { background:#0f1117; color:#e0e0e0; font-family:'Noto Sans TC',sans-serif; }
  .navbar { background:#1a1d27 !important; border-bottom:1px solid #2a2d3a; }
  .card { background:#1a1d27; border:1px solid #2a2d3a; border-radius:12px; }
  .card-header { background:#21253a; border-bottom:1px solid #2a2d3a; font-weight:700; }
  .table { color:#e0e0e0; }
  .table th { color:#8899bb; font-size:.8rem; text-transform:uppercase; border-color:#2a2d3a; }
  .table td { border-color:#1f2235; vertical-align:middle; }
  .table tbody tr:hover { background:#1f2235; }
  .up   { color:#26c281; font-weight:600; }
  .down { color:#e74c3c; font-weight:600; }
  .flat { color:#aaa; }
  .badge-code { background:#2a2d3a; color:#7eb8f7; font-family:monospace; border-radius:6px; padding:2px 7px; }
  .stock-card { border-left:3px solid #3a7bd5; }
  .meta-tag { font-size:.75rem; color:#778; }
  .btn-refresh { background:#3a7bd5; border:none; }
  .btn-refresh:hover { background:#2a6bc5; }
  .section-title { font-size:1rem; font-weight:700; color:#7eb8f7; margin-bottom:1rem; }
  .tab-nav .nav-link { color:#778; border:none; }
  .tab-nav .nav-link.active { color:#fff; background:#21253a; border-radius:8px; }
  .watchlist-item { border-left: 3px solid; }
  .price-up { border-color:#26c281; }
  .price-down { border-color:#e74c3c; }
  .price-flat { border-color:#555; }
  .num { font-family:monospace; }
</style>
</head>
<body>
<nav class="navbar navbar-dark px-3 py-2">
  <span class="navbar-brand mb-0 h5">📊 台灣股市三大法人報告</span>
  <div class="d-flex align-items-center gap-2">
    <span class="meta-tag">資料日期：{{ date_display }}</span>
    <a href="/" class="btn btn-refresh btn-sm text-white">🔄 更新</a>
  </div>
</nav>

<div class="container-fluid py-3 px-3">

  {% if error %}
  <div class="alert alert-danger">{{ error }}</div>
  {% else %}

  <!-- 自選股 -->
  {% if watchlist_data %}
  <div class="mb-4">
    <div class="section-title">⭐ 自選股追蹤</div>
    <div class="row g-2">
      {% for s in watchlist_data %}
      <div class="col-6 col-md-4 col-lg-2">
        <div class="card watchlist-item {{ s.price_class }} h-100">
          <div class="card-body p-2">
            <div class="d-flex justify-content-between align-items-start">
              <span class="badge-code">{{ s.code }}</span>
              <span class="meta-tag">{{ s.name }}</span>
            </div>
            {% if s.price %}
            <div class="mt-2">
              <div class="fs-5 fw-bold num">{{ s.price.close }}</div>
              <div class="{{ s.change_class }} num" style="font-size:.85rem;">
                {{ s.price.change }} ({{ s.price.change_pct }}%)
              </div>
              <div class="meta-tag mt-1">量 {{ s.price.volume }} 張</div>
            </div>
            {% else %}
            <div class="meta-tag mt-2">無行情資料</div>
            {% endif %}
            {% if s.inst %}
            <hr style="border-color:#2a2d3a;margin:6px 0">
            <div style="font-size:.72rem;">
              <div>外資 <span class="{{ 'up' if s.inst.foreign_net > 0 else 'down' if s.inst.foreign_net < 0 else 'flat' }} num">{{ s.inst.foreign_net_fmt }}</span></div>
              <div>投信 <span class="{{ 'up' if s.inst.trust_net > 0 else 'down' if s.inst.trust_net < 0 else 'flat' }} num">{{ s.inst.trust_net_fmt }}</span></div>
              <div>三大 <span class="{{ 'up' if s.inst.total_net > 0 else 'down' if s.inst.total_net < 0 else 'flat' }} num">{{ s.inst.total_net_fmt }}</span></div>
            </div>
            {% endif %}
          </div>
        </div>
      </div>
      {% endfor %}
    </div>
  </div>
  {% endif %}

  <!-- 三大法人排行 -->
  <ul class="nav tab-nav mb-3" id="tabs">
    <li class="nav-item"><a class="nav-link active" href="#" onclick="showTab('foreign_buy',this)">🌍 外資買超</a></li>
    <li class="nav-item"><a class="nav-link" href="#" onclick="showTab('foreign_sell',this)">🌍 外資賣超</a></li>
    <li class="nav-item"><a class="nav-link" href="#" onclick="showTab('trust_buy',this)">📦 投信買超</a></li>
    <li class="nav-item"><a class="nav-link" href="#" onclick="showTab('total_buy',this)">🏆 三大合計</a></li>
  </ul>

  {% for tab_id, title, rows in tabs %}
  <div id="tab_{{ tab_id }}" class="tab-pane" style="{{ 'display:block' if loop.first else 'display:none' }}">
    <div class="card">
      <div class="card-header">{{ title }} Top {{ rows|length }}</div>
      <div class="table-responsive">
        <table class="table table-sm mb-0">
          <thead>
            <tr>
              <th>#</th><th>代號</th><th>名稱</th>
              <th class="text-end">外資買賣超</th>
              <th class="text-end">投信買賣超</th>
              <th class="text-end">自營買賣超</th>
              <th class="text-end">三大合計</th>
            </tr>
          </thead>
          <tbody>
            {% for r in rows %}
            <tr>
              <td class="meta-tag">{{ loop.index }}</td>
              <td><span class="badge-code">{{ r.code }}</span></td>
              <td style="font-size:.85rem;">{{ r.name }}</td>
              <td class="text-end num {{ 'up' if r.foreign_net > 0 else 'down' if r.foreign_net < 0 else 'flat' }}">{{ r.foreign_net_fmt }}</td>
              <td class="text-end num {{ 'up' if r.trust_net > 0 else 'down' if r.trust_net < 0 else 'flat' }}">{{ r.trust_net_fmt }}</td>
              <td class="text-end num {{ 'up' if r.dealer_net > 0 else 'down' if r.dealer_net < 0 else 'flat' }}">{{ r.dealer_net_fmt }}</td>
              <td class="text-end num {{ 'up' if r.total_net > 0 else 'down' if r.total_net < 0 else 'flat' }}">{{ r.total_net_fmt }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
  </div>
  {% endfor %}

  {% endif %}
</div>

<script>
function showTab(id, el) {
  document.querySelectorAll('.tab-pane').forEach(p => p.style.display = 'none');
  document.getElementById('tab_' + id).style.display = 'block';
  document.querySelectorAll('.tab-nav .nav-link').forEach(a => a.classList.remove('active'));
  el.classList.add('active');
  return false;
}
</script>
</body>
</html>
"""

# ── Flask 路由 ────────────────────────────────────────────────────

@app.route("/")
def index():
    date_str = find_latest_trading_date()
    if not date_str:
        return render_template_string(HTML, error="無法取得資料，請稍後再試", date_display="N/A",
                                      watchlist_data=[], tabs=[])

    date_display = f"{date_str[:4]}/{date_str[4:6]}/{date_str[6:]}"
    records = fetch_institutional(date_str)
    if not records:
        return render_template_string(HTML, error=f"{date_display} 無三大法人資料", date_display=date_display,
                                      watchlist_data=[], tabs=[])

    inst_map = {r["code"]: r for r in records}

    # 格式化所有資料
    def enrich(rows):
        for r in rows:
            r["foreign_net_fmt"] = fmt_shares(r["foreign_net"])
            r["trust_net_fmt"]   = fmt_shares(r["trust_net"])
            r["dealer_net_fmt"]  = fmt_shares(r["dealer_net"])
            r["total_net_fmt"]   = fmt_shares(r["total_net"])
        return rows

    top = 20
    tabs = [
        ("foreign_buy",  "🌍 外資買超", enrich(sorted(records, key=lambda x: x["foreign_net"], reverse=True)[:top])),
        ("foreign_sell", "🌍 外資賣超", enrich(sorted(records, key=lambda x: x["foreign_net"])[:top])),
        ("trust_buy",    "📦 投信買超", enrich(sorted(records, key=lambda x: x["trust_net"], reverse=True)[:top])),
        ("total_buy",    "🏆 三大法人合計買超", enrich(sorted(records, key=lambda x: x["total_net"], reverse=True)[:top])),
    ]

    # 自選股
    watchlist_data = []
    for s in get_watchlist():
        code = s["code"]
        price = fetch_stock_price(code, date_str)
        inst  = inst_map.get(code)
        if inst:
            inst["foreign_net_fmt"] = fmt_shares(inst["foreign_net"])
            inst["trust_net_fmt"]   = fmt_shares(inst["trust_net"])
            inst["total_net_fmt"]   = fmt_shares(inst["total_net"])

        # 判斷漲跌
        price_class  = "price-flat"
        change_class = "flat"
        if price:
            try:
                chg = float(price["change"].replace("+","").replace("▲","").replace("▼","-").replace("X","0").replace(",",""))
                if chg > 0:   price_class, change_class = "price-up", "up"
                elif chg < 0: price_class, change_class = "price-down", "down"
            except:
                pass

        watchlist_data.append({
            "code": code, "name": s.get("name", code),
            "price": price, "inst": inst,
            "price_class": price_class, "change_class": change_class,
        })

    return render_template_string(HTML,
        date_display=date_display,
        watchlist_data=watchlist_data,
        tabs=tabs,
        error=None,
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
