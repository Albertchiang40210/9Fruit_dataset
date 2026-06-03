import streamlit as st
import pandas as pd
import numpy as np
import pymysql  
import time
from datetime import datetime
import socket  
import json    
import cv2
import requests
import base64
import streamlit.components.v1 as components
import os                      # 👈 確保有 import os
from dotenv import load_dotenv # 👈 確保有 import dotenv
from auth import render_login_interface # 👈 完美引入獨立的登入驗證模組

# ==============================================================================
# 0. 🔐 初始化環境變數安全隔離 (SecOps 業界標準規範)
# ==============================================================================
# 自動尋找專案根目錄下的 .env 檔案並載入系統變數
load_dotenv()

# 從安全環境變數中讀取敏感憑證與配置，若讀取不到則設定 Fallback 預設值
NGROK_URL = os.getenv("NGROK_URL", "https://fallback-url.ngrok-free.dev")
FASTAPI_PORT = os.getenv("FASTAPI_PORT", "8888")
FASTAPI_API_URL = f"http://localhost:{FASTAPI_PORT}/api/upload_shot"

# ==============================================================================
# 1. ⚙️ Streamlit 核心視覺組態
# ==============================================================================
st.set_page_config(page_title="智慧無人水果商店", page_icon="🍎", layout="wide")

st.markdown("""
<style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="collapsedControl"] { display: none; }
    .main-title { font-family: 'Helvetica Neue', Arial, sans-serif; color: #2c3e50; font-weight: 700; text-align: center; margin-bottom: 30px; }
    .receipt-title { font-size: 1.25rem; font-weight: bold; color: #2c3e50; border-bottom: 2px solid #e67e22; padding-bottom: 8px; margin-bottom: 15px; }
    .metric-box { background: #fdfefe; border: 1px solid #e6e1da; padding: 15px; border-radius: 8px; text-align: center; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

FRUIT_CH_NAMES = {
    'apple': '🍎 富士紅蘋果', 'avocado': '🥑 頂級酪梨', 'banana': '🍌 台灣香蕉',
    'guava': '🟢 彰化芭樂', 'kiwi': '🥝 紐西蘭奇異果', 'mango': '🥭 枋山愛文芒果',
    'orange': '🍊 鮮甜香橙', 'peach': '🍑 水蜜桃', 'pineapple': '🍍 金鑽鳳梨',
    'checkout': '🛒 顧客結帳總計'
}

# ==============================================================================
# 2. 📊 資料庫核心連線組態
# ==============================================================================
DB_CONFIG = {
    'host': os.getenv("DB_HOST", "127.0.0.1"),
    'port': int(os.getenv("DB_PORT", 3306)),
    'user': os.getenv("DB_USER", "root"),
    'password': os.getenv("DB_PASSWORD"),  
    'database': os.getenv("DB_DATABASE", "fruittest"),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
    'connect_timeout': 2  
}

db_connected = False
try:
    conn = pymysql.connect(**DB_CONFIG); cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM products")
    cursor.close(); conn.close()
    db_connected = True
except Exception: pass

# ==============================================================================
# 📊 實時營運數據讀取函數群
# ==============================================================================
def fetch_real_products():
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT name, price, stock FROM products")
    rows = cursor.fetchall(); cursor.close(); conn.close()
    return {row['name']: {'price': row['price'], 'stock': row['stock']} for row in rows}

def fetch_real_logs():
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp as 時間, name as 品項, action_type as 類型, qty as 數量, note as 備註 FROM stock_logs ORDER BY id DESC LIMIT 10")
    rows = cursor.fetchall(); cursor.close(); conn.close()
    for row in rows: row['品項'] = FRUIT_CH_NAMES.get(row['品項'], row['品項'])
    return rows

def fetch_today_revenue():
    if not db_connected:
        return 0
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        cursor.execute("SELECT note FROM stock_logs WHERE timestamp LIKE %s AND action_type='📤 交易完成'", (f"{today_str}%",))
        rows = cursor.fetchall()
        cursor.close(); conn.close()
        
        calculated_revenue = 0
        for row in rows:
            note_str = row['note']
            if "金額:$" in note_str:
                try:
                    part = note_str.split("金額:$")[1]
                    price_val = int(part.split(" |")[0])
                    calculated_revenue += price_val
                except: pass
        return calculated_revenue
    except:
        return 0

# 實時刷新與狀態同步機制
if db_connected:
    DB_PRODUCTS = fetch_real_products()
    DB_LOGS = fetch_real_logs()
    TODAY_REVENUE = fetch_today_revenue()
    
    conn = pymysql.connect(**DB_CONFIG); cursor = conn.cursor()
    cursor.execute("SELECT * FROM system_sync WHERE sync_key='main'")
    sync_status = cursor.fetchone(); cursor.close(); conn.close()
    
    is_frozen = bool(sync_status['is_frozen'])
    current_cart = json.loads(sync_status['cart_json']) if sync_status['cart_json'] else {}
    final_total = sync_status['total_due']
    image_blob_data = sync_status['image_blob']
else:
    DB_PRODUCTS = {k: {'price': 35, 'stock': 50} for k in FRUIT_CH_NAMES.keys()}
    DB_LOGS = []
    TODAY_REVENUE = 0
    is_frozen = False; current_cart = {}; final_total = 0; image_blob_data = None

query_params = st.query_params
is_mobile_client = query_params.get("client") == "mobile"

# ==============================================================================
# 📱 模式 A：【消費者手機端】
# ==============================================================================
if is_mobile_client:
    st.markdown("<h1 class='main-title'>📱 手機 AI 水果掃描儀</h1>", unsafe_allow_html=True)
    with st.container(border=True):
        img_file = st.camera_input("請對準秤台上的水果按下拍攝鈕：", key="mobile_camera_input")
        if img_file is not None:
            if st.button("🚀 送出照片進行 AI 點驗", use_container_width=True):
                bytes_data = img_file.getvalue()
                base64_image = base64.b64encode(bytes_data).decode('utf-8')
                with st.spinner("⚡ 影像資料高速同步至收銀台..."):
                    try:
                        res = requests.post(FASTAPI_API_URL, json={"image": base64_image})
                        st.success("📤 資料傳輸成功！")
                        time.sleep(1.5); st.rerun()
                    except Exception as e:
                        st.error(f"❌ 無法連線至邊緣運算核心: {e}")

# ==============================================================================
# 🖥️ 模式 B：【大螢幕與管理後台】
# ==============================================================================
else:
    if "mode" not in st.query_params:
        st.query_params["mode"] = "POS"
    device_mode = st.query_params["mode"]

    nav_col1, nav_col2, _ = st.columns([2, 2, 5])
    if nav_col1.button("🖥️ 門市 POS 自助點驗大螢幕", use_container_width=True, type="primary" if device_mode == "POS" else "secondary"):
        st.query_params["mode"] = "POS"; st.rerun()
    if nav_col2.button("💻 賽博收銀中樞 (分權管理後台)", use_container_width=True, type="primary" if device_mode == "BOSS" else "secondary"):
        st.query_params["mode"] = "BOSS"; st.rerun()
        
    st.markdown("<hr style='margin-top: 10px; margin-bottom: 20px;'>", unsafe_allow_html=True)
    
    if device_mode == "POS":
        st.markdown("<h1 class='main-title'>🖥️ 門市自助收銀大螢幕 (POS Kiosk)</h1>", unsafe_allow_html=True)
        
        if not is_frozen:
            st.markdown(
                """
                <iframe src="about:blank" style="display:none;"></iframe>
                <script>
                    setTimeout(function() {
                        window.parent.location.reload();
                    }, 2000);
                </script>
                """, unsafe_allow_html=True
            )

        col_left, col_right = st.columns([6, 5])
        with col_left:
            with st.container(border=True):
                st.markdown("### 📸 AI 影像特徵辨識雷達")
                if is_frozen and image_blob_data:
                    nparr = np.frombuffer(image_blob_data, np.uint8); img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    st.image(cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB), caption="🛸 YOLOv8 實時特徵標記畫面", use_container_width=True)
                else:
                    TARGET_MOBILE_URL = f"{NGROK_URL}?client=mobile"
                    qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={TARGET_MOBILE_URL}"
                    st.markdown(f"<div style='text-align:center; padding: 40px 0;'><img src='{qr_api}'/><h3 style='margin-top:20px;'>🛒 請用手機掃碼開始拍照結帳</h3></div>", unsafe_allow_html=True)
        
        with col_right:
            with st.container(border=True):
                if is_frozen:
                    st.markdown("<div class='receipt-title'>🧾 AI 即時連動點驗明細</div>", unsafe_allow_html=True)
                    if current_cart and final_total > 0:
                        t_data = [{"商品品項": FRUIT_CH_NAMES.get(k, k), "商品單價": f"${DB_PRODUCTS.get(k, {'price': 0})['price']} 元", "點驗數量": f"x {v}", "小計金額": f"${DB_PRODUCTS.get(k, {'price': 0})['price']*v} 元"} for k, v in current_cart.items()]
                        st.table(t_data)
                        st.markdown(f"## 💰 應付總計： <span style='color:#e67e22;'>${final_total} 元</span>", unsafe_allow_html=True)
                    else:
                        st.warning("🤖 AI 標記雷達未偵測到已知水果特徵。請調整角度重新拍攝！")
                    
                    st.markdown("---")
                    
                    pay_method = st.radio("💳 請選擇結帳支付管道：", ["💵 現金結帳", "📱 智慧行動支付", "💳 信用卡 / 悠遊卡"], horizontal=True, key="pos_pay_method")
                    
                    btn_col1, btn_col2 = st.columns(2)
                    
                    if current_cart and final_total > 0:
                        if btn_col1.button("🏁 確認結帳並列印發票", use_container_width=True, type="primary"):
                            if db_connected:
                                conn = pymysql.connect(**DB_CONFIG); cursor = conn.cursor()
                                now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                
                                for fk, fq in current_cart.items():
                                    cursor.execute("UPDATE products SET stock = GREATEST(stock - %s, 0) WHERE name = %s", (fq, fk))
                                    single_item_total = DB_PRODUCTS.get(fk, {'price': 0})['price'] * fq
                                    log_note = f"金額:${single_item_total} | 管道:{pay_method}"
                                    cursor.execute("INSERT INTO stock_logs (timestamp, name, action_type, qty, note) VALUES (%s, %s, %s, %s, %s)", 
                                                   (now_time, fk, '📤 交易完成', f"-{fq}", log_note))
                                
                                cursor.execute("UPDATE system_sync SET is_frozen=0, cart_json='{}', total_due=0, image_blob=NULL WHERE sync_key='main'")
                                conn.commit(); cursor.close(); conn.close()
                            st.balloons(); st.success("🎉 交易成功！"); time.sleep(1.5); st.rerun()
                    else:
                        btn_col1.button("🏁 無法結帳 (購物車空)", use_container_width=True, disabled=True)
                    
                    if btn_col2.button("❌ 辨識錯誤，清空重拍", use_container_width=True, type="secondary"):
                        if db_connected:
                            conn = pymysql.connect(**DB_CONFIG); cursor = conn.cursor()
                            cursor.execute("UPDATE system_sync SET is_frozen=0, cart_json='{}', total_due=0, image_blob=NULL WHERE sync_key='main'")
                            conn.commit(); cursor.close(); conn.close()
                        st.rerun()
                else:
                    st.markdown("<div style='text-align:center; color:#7f8c8d; padding: 135px 0;'><h2>🧾 點驗明細櫃檯</h2><p>目前空置中。等待顧客掃碼拍照...</p></div>", unsafe_allow_html=True)

# ==============================================================================
# 💻 模式 B 後半：【分權管理後台】(已實作硬核 RBAC 核心安全分流)
# ==============================================================================
    else:
        # 🛡️ 第一關防禦：安全認證牆。未登入成功則強制停止執行後續畫面
        if not render_login_interface(DB_CONFIG, db_connected):
            st.stop()
            
        # 🔓 認證通過：渲染頂部歡迎與安全登出組態
        user_panel_col, logout_panel_col = st.columns([8, 2])
        user_panel_col.markdown(f"👤 當前在線：**{st.session_state.real_name}** ｜ 權限群組：`{st.session_state.user_role.upper()}`")
        if logout_panel_col.button("🚪 安全登出系統", use_container_width=True, type="secondary", key="system_logout_btn"):
            st.session_state.logged_in = False
            st.session_state.user_role = None
            st.rerun()
            
        st.markdown("---")

        db_light = "🟢 正常連線" if db_connected else "🔴 連線失敗"
        fastapi_light = "🔴 未啟動"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(0.1)
            if s.connect_ex(('127.0.0.1', int(FASTAPI_PORT))) == 0: fastapi_light = "🟢 監聽中"
            s.close()
        except Exception: pass
        ngrok_light = "🟡 未啟動"
        try:
            s_ngrok = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s_ngrok.settimeout(0.1)
            if s_ngrok.connect_ex(('127.0.0.1', 4040)) == 0: ngrok_light = "🟢 穿透中"
            s_ngrok.close()
        except Exception: pass
        yolo_light = "🟢 辨識完畢" if is_frozen else "🟢 記憶體就緒"

        st.markdown("<h1 class='main-title'>💼 Internet of Fruits — 遠端門市營運決策後台</h1>", unsafe_allow_html=True)
        
        status_cols = st.columns(4)
        status_cols[0].metric("MySQL 資料庫", db_light)
        status_cols[1].metric("YOLOv8 模型", yolo_light)
        status_cols[2].metric("FastAPI 網關", fastapi_light)
        status_cols[3].metric("ngrok 穿透", ngrok_light)
        
        st.markdown("---")
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1: st.markdown(f"<div class='metric-box'>📊 總上架品項<h2 style='color:#e67e22; margin:5px 0;'>{len(FRUIT_CH_NAMES) - 1} 種水果</h2></div>", unsafe_allow_html=True)
        
        total_stocks = sum([item['stock'] for k, item in DB_PRODUCTS.items() if k != 'checkout'])
        with col_m2: st.markdown(f"<div class='metric-box'>📦 目前全店總庫存<h2 style='color:#27ae60; margin:5px 0;'>{total_stocks} 個</h2></div>", unsafe_allow_html=True)
        with col_m3: st.markdown(f"<div class='metric-box'>💰 今日累計營業額<h2 style='color:#2980b9; margin:5px 0;'>${TODAY_REVENUE:,} 元</h2></div>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        col_dash_left, col_dash_right = st.columns([6, 5])
        
        # 📊 左側實時數據看板 (全體在線人員均可直接調閱)
        with col_dash_left:
            with st.container(border=True):
                st.markdown("<h3 style='color:#2c3e50; margin-top:0;'>📦 實時庫存與零售價格清單 (MySQL 直連)</h3>", unsafe_allow_html=True)
                stock_table = [{"水果代碼": k, "水果品項": v, "當前零售價": f"${DB_PRODUCTS[k]['price']} 元", "現有庫存量": f"{DB_PRODUCTS[k]['stock']} 個"} for k, v in FRUIT_CH_NAMES.items() if k != 'checkout']
                st.table(stock_table)
            st.markdown("<br>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown("<h3 style='color:#2c3e50; margin-top:0;'>📜 門市進出貨與庫存異動歷史日誌</h3>", unsafe_allow_html=True)
                if DB_LOGS: st.table(DB_LOGS)
                else: st.caption("✨ 目前暫無庫存異動紀錄日誌。")
                
        # 🕹️ 右側核心控制面板 (精準根據 Role 實作商務權限隔離)
        with col_dash_right:
            
            # 👑 頂級控制權限 A：快速價格調整 (僅限老闆 admin 存取)
            if st.session_state.user_role == "admin":
                with st.container(border=True):
                    st.markdown("<h3 style='color:#2c3e50; margin-top:0;'>🏷️ 快速商品調價控制面板 <span style='font-size:0.8rem; background:#e1f5fe; color:#0288d1; padding:2px 6px; border-radius:4px;'>👑 老闆專屬</span></h3>", unsafe_allow_html=True)
                    valid_fruits = [k for k in FRUIT_CH_NAMES.keys() if k != 'checkout']
                    target_fruit_price = st.selectbox("請選擇要修改價格的水果：", valid_fruits, format_func=lambda x: FRUIT_CH_NAMES[x], key="price_select")
                    current_p = DB_PRODUCTS[target_fruit_price]['price']
                    st.caption(f"💡 目前資料庫零售價為： ${current_p} 元")
                    new_price = st.number_input("請輸入全新零售價 (TWD)：", min_value=1, value=int(current_p), step=5)
                    if st.button("💾 儲存並同步更新至 MySQL", key="save_price_btn"):
                        if db_connected:
                            conn = pymysql.connect(**DB_CONFIG); cursor = conn.cursor()
                            cursor.execute("UPDATE products SET price=%s WHERE name=%s", (new_price, target_fruit_price))
                            conn.commit(); cursor.close(); conn.close()
                            st.success("🎉 價格變更寫入成功！")
                            time.sleep(0.5); st.rerun()
            else:
                st.info("🔒 【快速商品調價面板】已鎖定。此功能僅限管理員(老闆)帳號操作。")

            st.markdown("<br>", unsafe_allow_html=True)
            
            # 👑 頂級控制權限 B：交班財務重置 (僅限老闆 admin 存取，嚴防財務漏洞)
            if st.session_state.user_role == "admin":
                with st.container(border=True):
                    st.markdown("<h3 style='color:#c0392b; margin-top:0;'>🚨 門市閉店交班重置面板 <span style='font-size:0.8rem; background:#ffebee; color:#c62828; padding:2px 6px; border-radius:4px;'>👑 老闆專屬</span></h3>", unsafe_allow_html=True)
                    st.caption("⚠️ 此操作會清空資料庫中「今日的交易明細日誌」，讓營業額完全歸零 ($0 元)。")
                    if st.button("🔄 盤點歸零：重置今日營業額", use_container_width=True, type="secondary", key="reset_revenue_btn"):
                        if db_connected:
                            conn = pymysql.connect(**DB_CONFIG); cursor = conn.cursor()
                            today_str = datetime.now().strftime("%Y-%m-%d")
                            cursor.execute("DELETE FROM stock_logs WHERE timestamp LIKE %s AND action_type='📤 交易完成'", (f"{today_str}%",))
                            conn.commit(); cursor.close(); conn.close()
                            st.toast("🧹 今日營業額已成功重置歸零！")
                            time.sleep(0.5); st.rerun()
            else:
                st.info("🔒 【交班財務重置面板】已鎖定。門市員工無權重置營業額數據。")

            st.markdown("<br>", unsafe_allow_html=True)
            
            # 🛠️ 通用核心權限 C：門市進補貨/報廢登錄管理 (全員 admin & staff 均可用)
            with st.container(border=True):
                st.markdown("<h3 style='color:#2c3e50; margin-top:0;'>📥 庫存進出貨異動登錄管理 <span style='font-size:0.8rem; background:#e8f5e9; color:#2e7d32; padding:2px 6px; border-radius:4px;'>🟢 全員可用</span></h3>", unsafe_allow_html=True)
                valid_fruits_stock = [k for k in FRUIT_CH_NAMES.keys() if k != 'checkout']
                target_fruit_stock = st.selectbox("請選擇要異動庫存的水果：", valid_fruits_stock, format_func=lambda x: FRUIT_CH_NAMES[x], key="stock_select")
                current_s = DB_PRODUCTS[target_fruit_stock]['stock']
                st.caption(f"💡 目前資料庫帳面庫存： {current_s} 個")
                stock_action = st.radio("異動類型：", ["📥 廠商進貨 (增加庫存)", "📤 門市出貨/報廢 (減少庫存)"], horizontal=True, key="boss_stock_action")
                change_qty = st.number_input("請輸入異動數量：", min_value=1, value=10, step=1, key="boss_stock_qty")
                stock_note = st.text_input("異動備註原因：", placeholder="例如：大樹鄉新進貨、過期報廢品...", key="boss_stock_note")
                if st.button("📦 確認送出並更新 MySQL 庫存", key="save_stock_btn"):
                    if db_connected:
                        now_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                        if "📥" in stock_action: final_stock = current_s + change_qty; log_qty, log_type = f"+{change_qty}", "📥 進貨"
                        else: final_stock = max(current_s - change_qty, 0); log_qty, log_type = f"-{change_qty}", "📤 出貨"
                        conn = pymysql.connect(**DB_CONFIG); cursor = conn.cursor()
                        cursor.execute("UPDATE products SET stock=%s WHERE name=%s", (final_stock, target_fruit_stock))
                        cursor.execute("INSERT INTO stock_logs (timestamp, name, action_type, qty, note) VALUES (%s, %s, %s, %s, %s)", (now_time, target_fruit_stock, log_type, log_qty, stock_note if stock_note else "無"))
                        conn.commit(); cursor.close(); conn.close()
                        st.success(f"🎉 庫存異動成功！數據已記錄。")
                        time.sleep(0.5); st.rerun()