#!/bin/bash

echo "🚀 正在啟動 Python 虛擬環境 (.venv)..."
source .venv/bin/activate

# 🟢 1. 啟動 FastAPI，嚴格鎖定在 8888 埠口，並在背景非同步掛載
echo "🔌 1. 正在背景掛載 FastAPI 核心 AI 推論網關 (Port: 8888)..."
uvicorn live_predict_api:app --host 0.0.0.0 --port 8888 > /dev/null 2>&1 &

# 給背景程序 1 秒初始化時間
sleep 1

# 🟢 2. 啟動 ngrok 反向代理安全通道，對準 Streamlit 前台的 8501 埠口
echo "🌐 2. 正在背景建立 ngrok 反向代理安全通道 (對接 Streamlit Port: 8501)..."
ngrok http 8501 --log=stdout > /dev/null 2>&1 &

# 給背景程序 1.5 秒初始化時間
sleep 1.5

# 🟢 3. 在前台啟動 Streamlit 門市 Kiosk 自助收銀看板，嚴格鎖定在 8501 埠口
echo "🖥️ 3. 正在前台啟動 Streamlit 門市 Kiosk 自助收銀看板 (Port: 8501)..."
echo "------------------------------------------------------------------"
streamlit run boss_final.py --server.port 8501

#sh start.sh 一鍵啟動 
#後台帳密：boss123 boss789 老闆
         #staff01 staff789 員工