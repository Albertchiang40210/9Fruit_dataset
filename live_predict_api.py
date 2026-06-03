from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64
import json
import pymysql
import cv2
import numpy as np
from ultralytics import YOLO
import os
from dotenv import load_dotenv

# ==============================================================================
# 🔐 初始化組態與載入 YOLOv8 模型
# ==============================================================================
load_dotenv()

app = FastAPI()

# 🔴 核心防禦解鎖：全開跨網域（CORS），允許 4G 封包完美打入本機轉發埠口
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_CONFIG = {
    'host': os.getenv("DB_HOST", "127.0.0.1"),
    'port': int(os.getenv("DB_PORT", 3306)),
    'user': os.getenv("DB_USER", "root"),
    'password': os.getenv("DB_PASSWORD"),
    'database': os.getenv("DB_DATABASE", "fruittest"),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# 🚀 載入你的最佳權重模型（請確保權重路徑正確）
MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "best.pt")
model = YOLO(MODEL_PATH)

class ImagePayload(BaseModel):
    image: str
    member_phone: str = None  # 保持相容性，目前皆傳 None

# ==============================================================================
# 📡 萬能核心推論接口
# ==============================================================================
@app.post("/api/upload_shot")
async def upload_shot(payload: ImagePayload):
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
        
        # 5. 連動計算 MySQL 總價與存檔
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 查詢目前 MySQL 內的商品單價
        cursor.execute("SELECT name, price FROM products")
        product_rows = cursor.fetchall()
        price_map = {r['name']: r['price'] for r in product_rows}
        
        total_due = 0
        for fk, fq in cart.items():
            total_due += price_map.get(fk, 35) * fq
            
        # 6. 狀態機冷凍：更新 system_sync，啟動大螢幕自動刷新
        cart_json_str = json.dumps(cart)
        cursor.execute(
            "UPDATE system_sync SET is_frozen=1, cart_json=%s, total_due=%s, image_blob=%s WHERE sync_key='main'",
            (cart_json_str, total_due, blob_bytes)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {"status": "success", "identified": cart, "total_due": total_due}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "ready"}