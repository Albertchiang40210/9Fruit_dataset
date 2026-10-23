import streamlit as st
import db_manager
import time

MAX_ATTEMPTS = 5
LOCK_SECONDS = 60

def verify_user_credentials(username, password, db_config, db_connected):
    """透過連線池驗證帳號密碼（雜湊比對），回傳使用者資訊或 None"""
    if not db_connected:
        st.error("🔴 資料庫未連線，無法驗證權限！")
        return None
    try:
        return db_manager.verify_user(username, password)
    except Exception as e:
        print(f"auth query failed: {e}")
        st.error("🔑 權限資料庫查詢異常，請稍後再試")
        return None

def render_login_interface(db_config, db_connected):
    """渲染高度擬真的商業登入牆"""
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.session_state.real_name = None

    if not st.session_state.logged_in:
        st.markdown("<h2 style='text-align: center; color: #e67e22; margin-top: 50px;'>🏪 智慧無人商店 — 後台營運驗證中樞</h2>", unsafe_allow_html=True)
        
        _, login_card_col, _ = st.columns([3, 4, 3])
        with login_card_col:
            with st.container(border=True):
                st.markdown("#### 🔒 系統安全登入")
                input_user = st.text_input("👤 身分帳號 (Username)：", placeholder="請輸入員編或管理員帳號", key="login_username_input")
                input_pwd = st.text_input("🔑 密碼驗證 (Password)：", type="password", placeholder="請輸入安全密碼", key="login_password_input")
                
                locked_until = st.session_state.get("login_locked_until", 0)
                if st.button("🚀 安全認證登入", use_container_width=True, type="primary"):
                    if time.time() < locked_until:
                        st.error(f"⛔ 嘗試次數過多，請 {int(locked_until - time.time())} 秒後再試。")
                        return False
                    auth_result = verify_user_credentials(input_user, input_pwd, db_config, db_connected)
                    if auth_result:
                        st.session_state.logged_in = True
                        st.session_state.user_role = auth_result['role']
                        st.session_state.real_name = auth_result['real_name']
                        st.success(f"🎉 認證成功！歡迎回來，{auth_result['real_name']}。")
                        time.sleep(0.8)
                        st.rerun()
                    else:
                        st.session_state.login_failures = st.session_state.get("login_failures", 0) + 1
                        if st.session_state.login_failures >= MAX_ATTEMPTS:
                            st.session_state.login_locked_until = time.time() + LOCK_SECONDS
                            st.session_state.login_failures = 0
                        time.sleep(1)
                        st.error("❌ 密碼認證錯誤或帳號不存在，請重新輸入！")
        return False
    return True