# 🍎 AI Smart Retail: 9-Class Fruit Recognition & Automated Checkout

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![YOLO](https://img.shields.io/badge/AI-YOLO26%20%2F%20Ultralytics-green)](https://github.com/ultralytics/ultralytics)
[![MySQL](https://img.shields.io/badge/Database-MySQL%208-orange)](https://www.mysql.com/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-red)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-ff4b4b)](https://streamlit.io/)

智慧零售／無人自助結帳系統:顧客用手機掃 QR Code 拍照,後端 YOLO 模型辨識 9 種水果,自動計價並同步到店內大螢幕,結帳後扣減 MySQL 庫存並記錄交易。

## 🚀 功能

- **物件偵測**:Ultralytics YOLO(`yolo26m` 微調),辨識 9 類水果。
- **硬體加速**:自動選擇 Apple Silicon `mps` 或 NVIDIA `cuda`,否則使用 CPU。
- **FastAPI 推論後端**(`live_predict_api.py`):`POST /api/upload_shot` 以 `X-API-Key` 驗證;價格查詢有 5 分鐘快取。
- **Streamlit 前端**(`boss_final.py`):顧客拍照端、店內大螢幕、含登入與角色權限的管理後台(營收圖表、庫存、價格)。
- **MySQL 連線池**(`db_manager.py`):`DBUtils.PooledDB`;結帳扣庫存在單一交易內完成。
- **登入安全**:密碼以 PBKDF2-SHA256 加鹽雜湊儲存;舊的明碼資料會在首次登入時自動升級。

## 🏗️ 架構

```
手機/攝影機 ──> Streamlit (boss_final.py, :8501) ──HTTP + X-API-Key──> FastAPI (live_predict_api.py, :8000)
                       ▲                                                    │ YOLO 推論
                       │ 輪詢 system_sync                                    ▼
                       └────────────────────── MySQL (db_manager.py) <── 寫入辨識結果 / 總價
```

## 📂 目錄結構

```
├── boss_final.py          # Streamlit 前端(顧客端 / 大螢幕 / 管理後台)
├── live_predict_api.py    # FastAPI 推論 API
├── db_manager.py          # MySQL 連線池、商品/交易/使用者邏輯
├── auth.py                # Streamlit 登入介面
├── train.py               # 模型訓練
├── test_model.py          # 本機批次推論測試
├── tests/                 # pytest 測試(雜湊、API 驗證)
├── perfect_merge.py       # 資料集合併工具(tkinter)
├── data.yaml              # YOLO 資料集設定(9 類)
├── Dockerfile / docker-compose.yml / start.sh
├── requirements*.txt      # api / web / dev 依賴(已鎖版本)
├── .env.example           # 環境變數範本
├── ngrok_config.yml.example
├── images/ labels/        # 資料集
└── result/                # 訓練輸出與權重(不納入版本控制)
```

## 🍓 辨識類別

`apple`、`avocado`、`banana`、`guava`、`kiwi`、`mango`、`orange`、`peach`、`pineapple`(定義於 `data.yaml`)。

## 🛠️ 快速開始

### 1. 設定環境變數
```bash
cp .env.example .env
cp ngrok_config.yml.example ngrok_config.yml   # 需要外網展示時才需要
```
編輯 `.env`,至少設定 `DB_PASSWORD`、`API_KEY`(`openssl rand -hex 32`)、`ADMIN_PASSWORD`(首次建立 `admin` 帳號用)。
**`.env` 與 `ngrok_config.yml` 含機密,已被 `.gitignore` 排除,請勿提交。**

### 2a. Docker 一鍵啟動
```bash
docker compose up --build
```
前端 http://localhost:8501,API 文件 http://localhost:8000/docs 。權重檔(不在 git 中)請放在 `result/` 並讓 `YOLO_MODEL_PATH` 指向它,compose 會以唯讀掛載進容器。API 與前端使用不同的依賴檔,前端映像檔不含 YOLO/torch,容器以非 root 執行。

### 2b. 本機啟動
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # 開發/測試另可用 requirements-dev.txt
sh start.sh   # FastAPI :8888(可用 FASTAPI_PORT 覆寫)+ ngrok + Streamlit :8501
```
本機啟動時請把 `.env` 的 `DB_HOST`/`DB_PORT` 指向可連線的 MySQL(docker compose 的 MySQL 對外為 `127.0.0.1:3307`)。`start.sh` 會自動把前端指向本機 API。

### 3. 訓練與測試
```bash
python train.py        # 訓練(預設 device=mps,非 Mac 請自行修改)
python test_model.py   # 以 result/train-5/weights/best.pt 推論 images/train,輸出於 runs/detect/predict
```
`data.yaml` 使用相對路徑,請在專案根目錄執行。注意:`images/val` 有 3108 張圖片,但 `labels/val` 只有 134 個標註檔,沒有標註的圖片在訓練時會被當作背景,請確認是否符合預期。

### 4. 測試
```bash
pip install -r requirements-dev.txt && pytest -q
```
GitHub Actions(`.github/workflows/ci.yml`)會在每次 push 執行。

## 🔐 安全注意事項

- 機密一律放 `.env`,程式碼不再內建預設金鑰;`API_KEY` 未設定時 API 會拒絕啟動。
- `CORS_ORIGINS` 預設只允許 `http://localhost:8501`,部署時請改成實際前端網址。
- MySQL 埠只綁定 `127.0.0.1`;`.dockerignore` 確保 `.env` 不會被打包進映像檔。
- 登入連續失敗 5 次會鎖定 60 秒;重置營收需勾選確認並寫入稽核日誌。
- 結帳以資料庫中凍結的購物車為準並加鎖,避免重複結帳;營收來自 `transactions` 表。
- git 歷史已清除舊機密,但這些機密曾經公開,仍須視為外洩並更換。

## 📈 Roadmap

1. 匯出 ONNX / OpenVINO,支援無 GPU 的收銀終端。
2. 加入 ByteTrack 追蹤,避免重複計價。
3. 部署至雲端(AWS/GCP)並使用託管資料庫。

## 📄 授權

MIT License,詳見 [LICENSE](LICENSE)。
