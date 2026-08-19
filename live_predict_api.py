from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import base64
import json
import db_manager
import cv2
import numpy as np
from ultralytics import YOLO
import os
from dotenv import load_dotenv

# ==============================================================================
# 🔐 初始化組態與載入 YOLOv8 模型
# ==============================================================================
load_dotenv()

# 🚀 【升級點】加上專屬的 Swagger 測試大門標題與說明
app = FastAPI(
    title="🍎 AI 影像智慧結帳系統 (大腦 API)",
    description="資展全班第一名的 AI 結帳系統！負責接收前端影像、YOLOv8 辨識、MySQL 查價與結帳同步。",
    version="1.0.0"
)

# 🔐 API Key 設定
API_KEY_NAME = "X-API-Key"
API_KEY = os.getenv("API_KEY", "9fruit-super-secret-key")
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(status_code=403, detail="Could not validate credentials")

# 🔴 核心防禦解鎖：全開跨網域（CORS），允許 4G 封包完美打入本機轉發埠口
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 移除寫死的 DB_CONFIG，統一改由 db_manager 接管
# 快取商品價格，避免每次辨識都去查資料庫
PRICE_CACHE = {}
import time
LAST_CACHE_TIME = 0
CACHE_TTL = 300  # 300 秒 = 5 分鐘

def get_cached_price_map():
    global PRICE_CACHE, LAST_CACHE_TIME
    if not PRICE_CACHE or (time.time() - LAST_CACHE_TIME > CACHE_TTL):
        try:
            PRICE_CACHE = db_manager.get_price_list()
            LAST_CACHE_TIME = time.time()
        except Exception as e:
            print(f"Failed to fetch price list: {e}")
    return PRICE_CACHE


# 🚀 載入你的最佳權重模型並啟用硬體加速
MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "best.pt")
model = YOLO(MODEL_PATH)
import torch
if torch.backends.mps.is_available():
    model.to("mps")
elif torch.cuda.is_available():
    model.to("cuda")

# 定義前端要傳過來的包裹格式
class ImagePayload(BaseModel):
    image: str = Field(..., description="請傳入 Base64 格式的圖片字串")
    member_phone: str = Field(None, description="會員電話（選填）")

# ==============================================================================
# 📡 萬能核心推論接口
# ==============================================================================
@app.post("/api/upload_shot", summary="📷 接收前端照片並執行 YOLO 辨識結帳", tags=["AI 辨識核心"])
async def upload_shot(payload: ImagePayload, api_key: str = Depends(get_api_key)):
    """
    **運作邏輯：**
    1. 接收前端傳來的 Base64 影像。
    2. 呼叫 YOLOv8 模型進行特徵辨識。
    3. 計算水果種類與數量，連線 MySQL 查詢商品單價。
    4. 將標記結果存入 system_sync 資料表，觸發前端大螢幕更新。
    """
    try:
        # 1. 影像 Base64 數據解碼
        img_data = base64.b64decode(payload.image)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(status_code=400, detail="影像解碼失敗")
        
        # 2. YOLOv8 推論特徵標記
        results = model(img, conf=0.25)
        cart = {}
        
        # 3. 統計標記框數量
        for box in results[0].boxes:
            cls_id = int(box.cls[0])
            label_name = model.names[cls_id]
            cart[label_name] = cart.get(label_name, 0) + 1
            
        # 4. 繪製標記框至原圖中
        annotated_img = results[0].plot()
        _, img_encoded = cv2.imencode('.jpg', annotated_img)
        blob_bytes = img_encoded.tobytes()
        
        # 5. 從快取取得商品單價並計算總價
        price_map = get_cached_price_map()
        
        total_due = 0
        for fk, fq in cart.items():
            total_due += price_map.get(fk, 35) * fq
            
        # 6. 狀態機冷凍：更新 system_sync，啟動大螢幕自動刷新
        cart_json_str = json.dumps(cart)
        db_manager.update_system_sync(
            is_frozen=1,
            cart_json=cart_json_str,
            total_due=total_due,
            image_blob=blob_bytes
        )
        
        return {"status": "success", "identified": cart, "total_due": total_due}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health", summary="🩺 系統健康檢查", tags=["系統監控"])
def health_check():
    """用來確認 FastAPI 伺服器與 YOLO 模型是否已經成功開機並準備好接收圖片。"""
    return {"status": "ready", "message": "大腦已上線，隨時可以開始辨識！"}