import os
import pymysql
import json
from datetime import datetime
from dbutils.pooled_db import PooledDB
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# Database Connection Pool Configuration
# ==============================================================================
_pool = None

def get_pool():
    global _pool
    if _pool is None:
        _pool = PooledDB(
            creator=pymysql,  # 使用 pymysql 模組
            maxconnections=100,  # 最大連線數
            mincached=5,         # 啟動時預先建立的空閒連線數
            maxcached=20,        # 連線池中最多可快取的空閒連線數
            blocking=True,       # 連線池用盡時，是否阻塞等待
            host=os.getenv("DB_HOST", "fruit_db"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", "P@ssw0rd"),
            database=os.getenv("DB_DATABASE", "fruit_store"),
            port=int(os.getenv("DB_PORT", 3306)),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=2
        )
    return _pool

def get_connection():
    """從連線池取得一個連線"""
    return get_pool().connection()

# ==============================================================================
# Helper Methods (Context Managers)
# ==============================================================================
class DBConnection:
    def __enter__(self):
        self.conn = get_connection()
        self.cursor = self.conn.cursor()
        return self.conn, self.cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.cursor.close()
        self.conn.close()

# ==============================================================================
# Business Logic Functions
# ==============================================================================

def check_db_connected():
    try:
        with DBConnection() as (conn, cursor):
            cursor.execute("SELECT COUNT(*) FROM products")
            return True
    except Exception as e:
        print(f"DB Connection Check Failed: {e}")
        return False

def init_db():
    """初始化 MySQL 資料庫：建立商品表與交易紀錄表，並預埋初始水果價格"""
    try:
        with DBConnection() as (conn, cursor):
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    name VARCHAR(50) PRIMARY KEY,
                    price INT NOT NULL,
                    stock INT NOT NULL DEFAULT 50
                )
            """)
            
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
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    timestamp DATETIME NOT NULL,
                    name VARCHAR(50) NOT NULL,
                    action_type VARCHAR(50) NOT NULL,
                    qty VARCHAR(20) NOT NULL,
                    note TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_sync (
                    sync_key VARCHAR(50) PRIMARY KEY,
                    is_frozen INT DEFAULT 0,
                    cart_json TEXT,
                    total_due INT DEFAULT 0,
                    image_blob MEDIUMBLOB
                )
            """)
            
            # 檢查是否已有商品，若無則預埋初始資料
            cursor.execute("SELECT COUNT(*) AS c FROM products")
            if cursor.fetchone()['c'] == 0:
                initial_fruits = [
                    ('apple', 25, 50), ('avocado', 45, 50), ('banana', 15, 50), ('guava', 30, 50), 
                    ('kiwi', 20, 50), ('mango', 50, 50), ('orange', 20, 50), ('peach', 40, 50), ('pineapple', 65, 50)
                ]
                cursor.executemany("INSERT INTO products (name, price, stock) VALUES (%s, %s, %s)", initial_fruits)
                print("🌱 [DATABASE] 初始水果價格已成功預埋至 MySQL！")
                
            cursor.execute("SELECT COUNT(*) AS c FROM system_sync WHERE sync_key='main'")
            if cursor.fetchone()['c'] == 0:
                cursor.execute("INSERT INTO system_sync (sync_key, is_frozen, cart_json, total_due) VALUES ('main', 0, '{}', 0)")
    except Exception as e:
        print(f"init_db failed: {e}")

def get_price_list():
    """從 MySQL 讀取最新的價目表"""
    with DBConnection() as (conn, cursor):
        cursor.execute("SELECT name, price FROM products")
        return {row['name']: row['price'] for row in cursor.fetchall()}

def get_all_products():
    with DBConnection() as (conn, cursor):
        cursor.execute("SELECT name, price, stock FROM products")
        rows = cursor.fetchall()
        return {row['name']: {'price': row['price'], 'stock': row['stock']} for row in rows}

def update_product_price(name, new_price):
    with DBConnection() as (conn, cursor):
        cursor.execute("UPDATE products SET price=%s WHERE name=%s", (new_price, name))

def update_product_stock(name, new_stock):
    with DBConnection() as (conn, cursor):
        cursor.execute("UPDATE products SET stock=%s WHERE name=%s", (new_stock, name))

def process_checkout(cart, pay_method):
    now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with DBConnection() as (conn, cursor):
        # 1. 更新庫存 & 寫入 logs
        for fk, fq in cart.items():
            cursor.execute("UPDATE products SET stock = GREATEST(stock - %s, 0) WHERE name = %s", (fq, fk))
            
            cursor.execute("SELECT price FROM products WHERE name = %s", (fk,))
            row = cursor.fetchone()
            price = row['price'] if row else 0
            single_item_total = price * fq
            
            log_note = f"金額:${single_item_total} | 管道:{pay_method}"
            cursor.execute(
                "INSERT INTO stock_logs (timestamp, name, action_type, qty, note) VALUES (%s, %s, %s, %s, %s)",
                (now_time, fk, '📤 交易完成', f"-{fq}", log_note)
            )
            
        # 2. 解凍大螢幕
        cursor.execute(
            "UPDATE system_sync SET is_frozen=0, cart_json='{}', total_due=0, image_blob=NULL WHERE sync_key='main'"
        )

def reset_system_sync():
    with DBConnection() as (conn, cursor):
        cursor.execute("UPDATE system_sync SET is_frozen=0, cart_json='{}', total_due=0, image_blob=NULL WHERE sync_key='main'")

def add_stock_log(name, action_type, qty, note):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    with DBConnection() as (conn, cursor):
        cursor.execute(
            "INSERT INTO stock_logs (timestamp, name, action_type, qty, note) VALUES (%s, %s, %s, %s, %s)",
            (timestamp, name, action_type, qty, note)
        )

def get_recent_logs(limit=10):
    with DBConnection() as (conn, cursor):
        cursor.execute(
            "SELECT timestamp as 時間, name as 品項, action_type as 類型, qty as 數量, note as 備註 FROM stock_logs ORDER BY id DESC LIMIT %s",
            (limit,)
        )
        return cursor.fetchall()

def get_today_revenue():
    today_str = datetime.now().strftime("%Y-%m-%d")
    with DBConnection() as (conn, cursor):
        cursor.execute(
            "SELECT note FROM stock_logs WHERE timestamp LIKE %s AND action_type='📤 交易完成'",
            (f"{today_str}%",)
        )
        rows = cursor.fetchall()
        
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

def reset_today_revenue():
    today_str = datetime.now().strftime("%Y-%m-%d")
    with DBConnection() as (conn, cursor):
        cursor.execute(
            "DELETE FROM stock_logs WHERE timestamp LIKE %s AND action_type='📤 交易完成'",
            (f"{today_str}%",)
        )

def get_system_sync():
    with DBConnection() as (conn, cursor):
        cursor.execute("SELECT * FROM system_sync WHERE sync_key='main'")
        return cursor.fetchone()

def update_system_sync(is_frozen, cart_json, total_due, image_blob=None):
    with DBConnection() as (conn, cursor):
        if image_blob is not None:
            cursor.execute(
                "UPDATE system_sync SET is_frozen=%s, cart_json=%s, total_due=%s, image_blob=%s WHERE sync_key='main'",
                (is_frozen, cart_json, total_due, image_blob)
            )
        else:
            cursor.execute(
                "UPDATE system_sync SET is_frozen=%s, cart_json=%s, total_due=%s, image_blob=NULL WHERE sync_key='main'",
                (is_frozen, cart_json, total_due)
            )
            
def check_frozen_status():
    with DBConnection() as (conn, cursor):
        cursor.execute("SELECT is_frozen FROM system_sync WHERE sync_key='main'")
        row = cursor.fetchone()
        return row['is_frozen'] if row else 0