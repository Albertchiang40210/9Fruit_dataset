# 🍎 AI Smart Retail: 9-Class Fruit Recognition & Automated Checkout System

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![YOLOv8](https://img.shields.io/badge/AI-YOLOv8%20%2F%20Ultralytics-green)](https://github.com/ultralytics/ultralytics)
[![MySQL](https://img.shields.io/badge/Database-MySQL-orange)](https://www.mysql.com/)
[![Framework](https://img.shields.io/badge/API-FastAPI-red)](https://fastapi.tiangolo.com/)

這是一個專為智慧零售（Smart Retail）與無人自助結帳場景設計的 **端到端（End-to-End）AI 影像辨識與庫存管理系統**。系統能透過攝影機即時辨識 9 種常見水果，自動計算金額，並與後端 MySQL 資料庫連動，實現自動化扣減庫存與建立訂單，同時支援透過 API 與 ngrok 進行雲地端整合測試。

---

## 🚀 核心技術亮點 (Key Features)

- **多目標物件偵測 (Object Detection):** 基於 YOLOv8 進行客製化模型訓練，能精準辨識多種水果並處理邊界框疊加問題。
- **硬體加速推理 (Hardware Acceleration):** 針對 Apple Silicon 架構，程式碼原生支援 `device="mps"` (Metal Performance Shaders) 進行 GPU 加速，大幅提升 Local 端推理幀率 (FPS)。
- **自動化資料庫整合 (Database Integration):** 辨識結果直接串接 `db_manager.py`，採用交易（Transaction）機制，防範高並發狀況下的庫存資料衝突。
- **即時串流部署 (API & MLOps Ready):** 內建 `live_predict_api.py`，並預配置 `ngrok_config.yml`，可快速將地端 AI 推理能力拓展為公網 API 服務，便於前後端分離開發與行動端測試。

---

## 📐 系統架構圖 (System Architecture)

[ 攝影機 / 影像輸入 ] ──> [ YOLOv8 模型推理 (MPS 加速) ]
│
▼ (辨識類別與數量)
[ live_predict_api.py ]
│
▼ (SQL 交易處理)
[ db_manager.py (MySQL) ] ──> [ 更新庫存 / 產生訂單 ]

---

## 📂 專案目錄結構 (Project Structure)

9FRUIT_DATASET/
├── .env                  # 環境變數設定 (資料庫密碼等)
├── data.yaml             # YOLO 模型訓練資料集設定檔 (定義 9 種水果類別)
├── train.py              # 模型訓練與優化腳本
├── test_model.py         # 本地端圖片/影片推理測試腳本 (支援 MPS 加速)
├── db_manager.py         # MySQL 資料庫連線與 SQL 增刪查改 (CRUD) 核心邏輯
├── live_predict_api.py   # 基於 Web 框架開發的即時辨識與串流 API
├── ngrok_config.yml      # ngrok 外網對應設定檔，用於公網展示 Demo
├── images/               # 測試與訓練影像資料夾
└── result/               # 模型訓練權重 (.pt) 與推論結果輸出路徑

🍓 支援辨識之水果類別 (Dataset Classes)
本專案針對以下 9 種熱帶與溫帶常見水果進行最佳化訓練：
	1.	蘋果 (Apple) | 2. 香蕉 (Banana) | 3. 橘子 (Orange) | 4. 檸檬 (Lemon) | 5. 葡萄 (Grape)
	2.	鳳梨 (Pineapple) | 7. 西瓜 (Watermelon) | 8. 芒果 (Mango) | 9. 草莓 (Strawberry)
🛠️ 快速開始 (Getting Started)
1. 環境安裝
請確保環境已安裝 Python 3.10+，並執行以下指令安裝依賴套件：
pip install ultralytics pymysql fastapi uvicorn requests

2. 資料庫配置
在 MySQL 中建立相應的資料表（如 inventory 與 orders），並在 .env 檔案中設定您的連線資訊：
DB_HOST=localhost
DB_USER=your_username
DB_PASSWORD=your_password
DB_NAME=fruit_retail

3. 執行模型推理測試
執行以下腳本，系統會自動載入最佳權重 best.pt 並對 images/train 資料夾下的水果進行辨識，結果將儲存於 runs/detect/predict：
python test_model.py

4. 啟動即時 API 服務與外網穿透
# 啟動 API 後端
python live_predict_api.py

# 啟動 ngrok 進行外網對應 (需先設定 ngrok_config.yml)
ngrok start --config ngrok_config.yml --all

📈 未來優化方向 (Future Roadmap)
	1.	模型輕量化: 將 .pt 模型導出為 ONNX 或 OpenVINO 格式，以利在無 GPU 的低成本收銀終端上流暢運行。
	2.	多目標追蹤 (Object Tracking): 引入 ByteTrack 演算法，防止顧客在移動水果時造成重複計價或漏刷。
	3.	雲端微服務化: 將整個專案封裝為 Docker 鏡像，並部署至 AWS EC2 / GCP，結合雲端 RDS 資料庫。
