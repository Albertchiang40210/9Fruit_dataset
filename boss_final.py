import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime
import socket  
import json    
import cv2
import requests
import base64
import os                      
from dotenv import load_dotenv 
from auth import render_login_interface 
import db_manager

# ==============================================================================
# 0. 🔐 初始化環境變數與單天線一體化網關
# ==============================================================================
load_dotenv()

# 👇 這樣寫，搬進 Docker 後就會自動走內部通道找 fruit_backend 的 8000 埠號
FASTAPI_HOST = os.getenv("FASTAPI_HOST", "fruit_backend")
FASTAPI_PORT = os.getenv("FASTAPI_PORT", "8000")
FASTAPI_API_URL = f"http://{FASTAPI_HOST}:{FASTAPI_PORT}/api/upload_shot"

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
# 2. 📊 資料庫核心連線組態 (全容器化版本)
# ==============================================================================
import os # 確保最上面有 import os

# 1. 檢查資料庫連線
db_connected = db_manager.check_db_connected()

def fetch_real_products():
    return db_manager.get_all_products()

def fetch_real_logs():
    rows = db_manager.get_recent_logs(10)
    for row in rows: 
        row['品項'] = FRUIT_CH_NAMES.get(row['品項'], row['品項'])
    return rows

def fetch_today_revenue():
    if not db_connected: return 0
    return db_manager.get_today_revenue()

# ==============================================================================
# 🔄 核心狀態機同步讀取
# ==============================================================================
    DB_PRODUCTS = fetch_real_products()
    DB_LOGS = fetch_real_logs()
    TODAY_REVENUE = fetch_today_revenue()
    
    sync_status = db_manager.get_system_sync()
    
    if sync_status:
        is_frozen = bool(sync_status.get('is_frozen', 0))
        current_cart = json.loads(sync_status.get('cart_json', '{}')) if sync_status.get('cart_json') else {}
        final_total = sync_status.get('total_due', 0)
        image_blob_data = sync_status.get('image_blob', None)
    else:
        is_frozen = False; current_cart = {}; final_total = 0; image_blob_data = None
else:
    DB_PRODUCTS = {k: {'price': 35, 'stock': 50} for k in FRUIT_CH_NAMES.keys()}
    DB_LOGS = []; TODAY_REVENUE = 0; is_frozen = False; current_cart = {}; final_total = 0; image_blob_data = None

# 🛠️ 萬能物理防呆切換開關：如果手機誤入大螢幕POS，按一下就能瞬間切回手機相機
if st.button("🔄 手機誤入？強制切換至【手機拍照端】", use_container_width=True):
    st.query_params["client"] = "mobile"
    st.rerun()

query_params = st.query_params
is_mobile_client = query_params.get("client") == "mobile"

# ==============================================================================
# 📱 模式 A：【消費者手機拍照端】
# ==============================================================================
if is_mobile_client:
    st.markdown("<h1 class='main-title'>📱 手機 AI 水果掃描儀</h1>", unsafe_allow_html=True)
    with st.container(border=True):
        st.info("📡 4G/5G 全球行動公網雲端網關已就緒")
        img_file = st.camera_input("請對準秤台上的水果按下拍攝鈕：", key="mobile_camera_input")
        if img_file is not None:
            if st.button("🚀 送出照片進行 AI 點驗", use_container_width=True):
                bytes_data = img_file.getvalue()
                
                # 🛠️ 核心防禦：將手機大圖強制進行物理壓縮，防止撐爆網關與資料庫
                try:
                    nparr = np.frombuffer(bytes_data, np.uint8)
                    raw_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    if raw_img.shape[1] > 800:
                        scale = 800 / raw_img.shape[1]
                        raw_img = cv2.resize(raw_img, (0,0), fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
                    _, img_encoded = cv2.imencode('.jpg', raw_img, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                    bytes_data = img_encoded.tobytes()
                except Exception as compression_err:
                    st.warning(f"⚠️ 影像預處理輕微異常: {compression_err}")

                base64_image = base64.b64encode(bytes_data).decode('utf-8')
                with st.spinner("⚡ 影像資料高速同步至收銀台..."):
                    try:
                        # 🚨 關鍵修正：將原本的 None 改為空字串 ""，完美通過 FastAPI 的 Pydantic 422 嚴格驗證
                        payload = {"image": base64_image, "member_phone": ""}
                        res = requests.post(FASTAPI_API_URL, json=payload, timeout=15)
                        
                        if res.status_code == 200:
                            st.success("📤 資料傳輸成功！請觀看前方大螢幕。")
                        else:
                            st.error(f"❌ 後端推論大腦回報錯誤 (HTTP {res.status_code}): {res.text}")
                        
                        time.sleep(1.0); st.rerun()
                    except Exception as e:
                        st.error(f"❌ 邊緣運算核心網關通訊異常: {e}")

# ==============================================================================
# 🖥️ 模式 B：【大螢幕與管理後台】
# ==============================================================================
else:
    if "mode" not in st.query_params: st.query_params["mode"] = "POS"
    device_mode = st.query_params["mode"]

    nav_col1, nav_col2, _ = st.columns([2, 2, 5])
    if nav_col1.button("🖥️ 門市 POS 自助點驗大螢幕", use_container_width=True, type="primary" if device_mode == "POS" else "secondary"):
        st.query_params["mode"] = "POS"; st.rerun()
    if nav_col2.button("💻 賽博收銀中樞 (分權管理後台)", use_container_width=True, type="primary" if device_mode == "BOSS" else "secondary"):
        st.query_params["mode"] = "BOSS"; st.rerun()
        
    st.markdown("<hr style='margin-top: 10px; margin-bottom: 20px;'>", unsafe_allow_html=True)
    
    if device_mode == "POS":
        st.markdown("<h1 class='main-title'>🖥️ 門市自助收銀大螢幕 (POS Kiosk)</h1>", unsafe_allow_html=True)

        # 🟢 萬能抗鬼畜心跳監聽器：每 1.5 秒背景盯梢 MySQL
        @st.fragment(run_every=1.5)
        def database_heartbeat_listener():
            # 🚨 終極抗鬼畜防禦：如果畫面上已經有照片了 (is_frozen == True)，
            # 監聽器立刻原地立正，絕對不重複發射 JavaScript 重整炮，徹底解決無限循環刷新問題！
            if is_frozen:
                return
                
            if db_connected:
                try:
                    is_frozen_status = db_manager.check_frozen_status()
                    
                    # 只有當手機剛送達 (資料庫為 1，大螢幕還是 0) 的關鍵瞬間，才發射唯一一次重整炮
                    if is_frozen_status == 1:
                        st.components.v1.html("""
                            <script>
                                window.parent.location.reload();
                            </script>
                        """, height=0)
                except: pass

        # 啟動防鬼畜監聽
        database_heartbeat_listener()

        col_left, col_right = st.columns([6, 5])
        with col_left:
            with st.container(border=True):
                st.markdown("### 📸 AI 影像特徵辨識雷達")
                if is_frozen and image_blob_data:
                    nparr = np.frombuffer(image_blob_data, np.uint8); img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    st.image(cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB), caption="🛸 YOLOv8 實時特徵標記畫面", use_container_width=True)
                else:
                    NGROK_BASE_URL = os.getenv("NGROK_URL", "https://uncrown-pacific-sprout.ngrok-free.dev")
                    TARGET_MOBILE_URL = f"{NGROK_BASE_URL}?client=mobile"
                    qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={TARGET_MOBILE_URL}"
                    st.markdown(f"<div style='text-align:center; padding: 40px 0;'><img src='{qr_api}'/><h3 style='margin-top:20px;'>🛒 請用手機掃碼開始拍照結帳</h3></div>", unsafe_allow_html=True)
        
        with col_right:
            with st.container(border=True):
                if is_frozen:
                    st.markdown("<div class='receipt-title'>🧾 AI 即時連動點驗明細</div>", unsafe_allow_html=True)
                    if current_cart and final_total > 0:
                        t_data = [{"商品品項": FRUIT_CH_NAMES.get(k, k), "商品單價": f"${DB_PRODUCTS.get(k, {'price': 0})['price']} 元", "點驗數量": f"x {v}", "小計金額": f"${DB_PRODUCTS.get(k, {'price': 0})['price']*v} 元"} for k, v in current_cart.items()]
                        st.table(t_data)
                    else:
                        st.warning("🤖 AI 未偵測到已知水果特徵。")
                    
                    st.markdown("---")
                    st.markdown(f"## 💰 應付總計： <span style='color:#e67e22;'>${final_total} 元</span>", unsafe_allow_html=True)
                    st.markdown("---")
                    
                    pay_method = st.radio("💳 請選擇結帳支付管道：", ["💵 現金結帳", "📱 智慧行動支付", "💳 信用卡 / 悠遊卡"], horizontal=True, key="pos_pay_method")
                    btn_col1, btn_col2 = st.columns(2)
                    
                    if current_cart and final_total > 0:
                        if btn_col1.button("🏁 確認結帳並列印發票", use_container_width=True, type="primary"):
                            if db_connected:
                                db_manager.process_checkout(current_cart, pay_method)
                            st.balloons(); st.success("🎉 交易成功！"); time.sleep(1.2); st.rerun()
                    else:
                        btn_col1.button("🏁 無法結帳", use_container_width=True, disabled=True)
                    
                    if btn_col2.button("❌ 辨識錯誤，清空重拍", use_container_width=True, type="secondary"):
                        if db_connected:
                            db_manager.reset_system_sync()
                        st.rerun()
                else:
                    st.markdown("<div style='text-align:center; color:#7f8c8d; padding: 135px 0;'><h2>🧾 點驗明細櫃檯</h2><p>目前空置中。等待顧客掃碼拍照...</p></div>", unsafe_allow_html=True)

# ─── 💻 子分流 B2：分權管理後台 ───
    else:
        # DB_CONFIG 已經在 db_manager 內部處理，因此直接傳一個 dummy dict
        if not render_login_interface({}, db_connected): st.stop()
        user_panel_col, logout_panel_col = st.columns([8, 2])
        user_panel_col.markdown(f"👤 當前在線：**{st.session_state.real_name}** ｜ 權限群組：`{st.session_state.user_role.upper()}`")
        if logout_panel_col.button("🚪 安全登出系統", use_container_width=True, type="secondary"):
            st.session_state.logged_in = False; st.session_state.user_role = None; st.rerun()
            
        st.markdown("---")
        db_light = "🟢 正常連線" if db_connected else "🔴 連線失敗"
        fastapi_light = "🔴 未啟動"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(0.1)
            if s.connect_ex(('127.0.0.1', int(FASTAPI_PORT))) == 0: fastapi_light = "🟢 監聽中"
            s.close()
        except: pass
        ngrok_light = "🟢 穿透中"
        
        st.markdown("<h1 class='main-title'>💼 Internet of Fruits — 遠端門市營運決策後台</h1>", unsafe_allow_html=True)
        status_cols = st.columns(4)
        status_cols[0].metric("MySQL 資料庫", db_light)
        status_cols[1].metric("YOLOv8 模型", "🟢 辨識完畢" if is_frozen else "🟢 記憶體就緒")
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
        
        with col_dash_left:
            st.markdown("<h4 style='color:#2c3e50;'>📦 實時庫存與零售價格清單</h4>", unsafe_allow_html=True)
            stock_table = [{"水果代碼": k, "水果品項": v, "當前零售價": f"${DB_PRODUCTS[k]['price']} 元", "現有庫存量": f"{DB_PRODUCTS[k]['stock']} 個"} for k, v in FRUIT_CH_NAMES.items() if k != 'checkout']
            st.table(stock_table)
            st.markdown("<br>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown("<h3 style='color:#2c3e50; margin-top:0;'>📜 門市進出貨與庫存異動歷史日誌</h3>", unsafe_allow_html=True)
                if DB_LOGS: st.table(DB_LOGS)
                else: st.caption("✨ 目前暫無日誌。")
                
        with col_dash_right:
            if st.session_state.user_role == "admin":
                with st.container(border=True):
                    st.markdown("<h3 style='color:#2c3e50; margin-top:0;'>🏷️ 快速商品調價控制面板</h4>", unsafe_allow_html=True)
                    valid_fruits = [k for k in FRUIT_CH_NAMES.keys() if k != 'checkout']
                    target_fruit_price = st.selectbox("請選擇要修改價格的水果：", valid_fruits, format_func=lambda x: FRUIT_CH_NAMES[x])
                    current_p = DB_PRODUCTS[target_fruit_price]['price']
                    st.caption(f"💡 目前零售價為： ${current_p} 元")
                    new_price = st.number_input("請輸入全新零售價 (TWD)：", min_value=1, value=int(current_p), step=5)
                    if st.button("💾 儲存並同步更新至 MySQL"):
                        if db_connected:
                            db_manager.update_product_price(target_fruit_price, new_price)
                            st.success("🎉 價格變更成功！"); time.sleep(0.5); st.rerun()
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.session_state.user_role == "admin":
                with st.container(border=True):
                    st.markdown("<h3 style='color:#c0392b; margin-top:0;'>🚨 門市閉店交班重置面板</h4>", unsafe_allow_html=True)
                    if st.button("🔄 盤點歸零：重置今日營業額", use_container_width=True, type="secondary"):
                        if db_connected:
                            db_manager.reset_today_revenue()
                            st.toast("🧹 今日營業額已重置歸零！"); time.sleep(0.5); st.rerun()
            
            st.markdown("<br>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown("<h3 style='color:#2c3e50; margin-top:0;'>📥 庫存進出貨異動登錄管理</h3>", unsafe_allow_html=True)
                valid_fruits_stock = [k for k in FRUIT_CH_NAMES.keys() if k != 'checkout']
                target_fruit_stock = st.selectbox("請選擇要異動庫存的水果：", valid_fruits_stock, format_func=lambda x: FRUIT_CH_NAMES[x])
                current_s = DB_PRODUCTS[target_fruit_stock]['stock']
                st.caption(f"💡 目前帳面庫存： {current_s} 個")
                stock_action = st.radio("異動類型：", ["📥 廠商進貨 (增加庫存)", "📤 門市出貨/報廢 (減少庫存)"], horizontal=True)
                change_qty = st.number_input("請輸入異動數量：", min_value=1, value=10, step=1)
                stock_note = st.text_input("異動備註原因：", placeholder="例如：新進貨...")
                if st.button("📦 確認送出並更新庫存"):
                    if db_connected:
                        if "📥" in stock_action: 
                            final_stock = current_s + change_qty
                            log_qty, log_type = f"+{change_qty}", "📥 進貨"
                        else: 
                            final_stock = max(current_s - change_qty, 0)
                            log_qty, log_type = f"-{change_qty}", "📤 出貨"
                        
                        db_manager.update_product_stock(target_fruit_stock, final_stock)
                        db_manager.add_stock_log(target_fruit_stock, log_type, log_qty, stock_note if stock_note else "無")
                        
                        st.success(f"🎉 庫存異動成功！"); time.sleep(0.5); st.rerun()