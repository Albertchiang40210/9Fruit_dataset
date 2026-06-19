import os
import pymysql
import json
from datetime import datetime

def get_connection():
    """建立與 Docker 內部 MySQL 的連線"""
    # 這裡的 host 填寫 'fruit_db'，對應 docker-compose.yml 裡面的服務名稱
    return pymysql.connect(
        host="fruit_db",
        user="root",
        password="P@ssw0rd",  # ⚠️ 這裡要跟你的 docker-compose.yml 密碼一模一樣
        database="fruit_store",          # ⚠️ 這裡要跟你的 docker-compose.yml 資料庫名稱一模一樣
        port=3306,                      # Docker 內部互連一律用預設的 3306
        cursorclass=pymysql.cursors.Cursor
    )

def init_db():
    """初始化 MySQL 資料庫：建立商品表與交易紀錄表，並預埋初始水果價格"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. 建立商品價格表 (VARCHAR 在 MySQL 中必須指定長度)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            name VARCHAR(50) PRIMARY KEY,
            price INT NOT NULL
        )
    """)
    
    # 2. 建立交易紀錄表 (MySQL 使用 INT AUTO_INCREMENT)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            timestamp DATETIME NOT NULL,
            items_json TEXT NOT NULL,
            total_due INT NOT NULL,
            cash_paid INT NOT NULL,
            change_given INT NOT NULL
        )
    """)
    
    # 檢查是否已有商品，若無則預埋初始資料
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        initial_fruits = [
            ('apple', 25), ('avocado', 45), ('banana', 15), ('guava', 30), 
            ('kiwi', 20), ('mango', 50), ('orange', 20), ('peach', 40), ('pineapple', 65)
        ]
        # ⚠️ 注意：MySQL 的預留預留佔位符必須是 %s，不能用 SQLite 的 ?
        cursor.executemany("INSERT INTO products VALUES (%s, %s)", initial_fruits)
        print("🌱 [DATABASE] 初始水果價格已成功預埋至 MySQL！")
        
    conn.commit()
    conn.close()

def get_price_list():
    """從 MySQL 讀取最新的價目表，供主程式 YOLO 使用"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, price FROM products")
    prices = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return prices

def save_transaction(items_dict, total, paid, change):
    """交易成功時，將整筆明細與找零寫入 MySQL 資料庫"""
    conn = get_connection()
    cursor = conn.cursor()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    items_json = json.dumps(items_dict)
    
    # ⚠️ 佔位符全部由 ? 改為 %s
    cursor.execute("""
        INSERT INTO transactions (timestamp, items_json, total_due, cash_paid, change_given)
        VALUES (%s, %s, %s, %s, %s)
    """, (timestamp, items_json, total, paid, change))
    
    conn.commit()
    conn.close()
    print(f"💾 [DATABASE] 交易已成功寫入 MySQL 資料庫！時間：{timestamp}")