import sqlite3
from datetime import datetime

DB_NAME = "cyber_kiosk.db"

def init_db():
    """初始化資料庫：建立商品表與交易紀錄表"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. 建立商品價格表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            name TEXT PRIMARY KEY,
            price INTEGER NOT NULL
        )
    """)
    
    # 2. 建立交易紀錄表 (收據)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            items_json TEXT NOT NULL,
            total_due INTEGER NOT NULL,
            cash_paid INTEGER NOT NULL,
            change_given INTEGER NOT NULL
        )
    """)
    
    # 預埋初始水果價格 (如果資料表是空的才寫入)
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        initial_fruits = [
            ('apple', 25), ('avocado', 45), ('banana', 15), ('guava', 30), 
            ('kiwi', 20), ('mango', 50), ('orange', 20), ('peach', 40), ('pineapple', 65)
        ]
        cursor.executemany("INSERT INTO products VALUES (?, ?)", initial_fruits)
        
    conn.commit()
    conn.close()

def get_price_list():
    """從資料庫讀取最新的價目表，供主程式 YOLO 使用"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name, price FROM products")
    prices = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return prices

def save_transaction(items_dict, total, paid, change):
    """交易成功時，將整筆明細與找零寫入資料庫"""
    import json
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    items_json = json.dumps(items_dict) # 把字典轉成字串存進去
    
    cursor.execute("""
        INSERT INTO transactions (timestamp, items_json, total_due, cash_paid, change_given)
        VALUES (?, ?, ?, ?, ?)
    """, (timestamp, items_json, total, paid, change))
    
    conn.commit()
    conn.close()
    print(f"💾 [DATABASE] 交易已成功寫入資料庫！時間：{timestamp}")