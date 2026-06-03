import os
import shutil
import csv
import tkinter as tk
from tkinter import filedialog

def select_dir(title_text):
    root = tk.Tk()
    root.withdraw()
    root.lift()
    root.attributes('-topmost', True)
    return filedialog.askdirectory(title=title_text)

def main():
    print("🎨 請用滑鼠點選【Fruits by YOLO】裡面的 【train】 資料夾...")
    csv_train_dir = select_dir("請點選 Fruits by YOLO 裡面的 【train】 資料夾")
    if not csv_train_dir: return

    csv_path = os.path.join(csv_train_dir, "_classes.csv")
    if not os.path.exists(csv_path):
        print("❌ 沒看到 _classes.csv！")
        return

    # 新基地路徑
    new_base = os.path.expanduser("~/Documents/Fruit_Grand_Dataset")
    new_img_dir = os.path.join(new_base, "train", "images")
    new_lbl_dir = os.path.join(new_base, "train", "labels")
    os.makedirs(new_img_dir, exist_ok=True)
    os.makedirs(new_lbl_dir, exist_ok=True)

    # 💰 終極 16 種水果生死簿
    FINAL_MAP = {
        'apple': 0, 'avocado': 1, 'banana': 2, 'guava': 3, 'kiwi': 4, 
        'mango': 5, 'orange': 6, 'peach': 7, 'pineapple': 8,
        'jackfruit': 9, 'litchi': 10, 'hog plum': 11, 'papaya': 12, 'grapes': 13,
        'sugerapple': 14, 'watermelon': 15
    }

    # 📋 Roboflow 下載格式的另一種常見對照表 (0~8 順序通常與 data.yaml 相同)
    ROBO_LIST = ['apple', 'banana', 'grapes', 'kiwi', 'mango', 'orange', 'pineapple', 'sugerapple', 'watermelon']

    print("🚀 暴力 CSV 解密機啟動，地毯式搜索每行資料...")
    merge_count = 0

    with open(csv_path, mode='r', encoding='utf-8') as f:
        # 自動偵測分隔符
        sample = f.read(2048)
        f.seek(0)
        delimiter = ';' if ';' in sample else ','
        reader = csv.reader(f, delimiter=delimiter)
        
        # 跳過第一行欄位頭
        header = next(reader)

        for row in reader:
            if len(row) < 2: continue
            
            img_name = row[0].strip()
            src_img_path = os.path.join(csv_train_dir, img_name)
            
            # 如果這行照片根本不存在，就跳過
            if not os.path.exists(src_img_path):
                continue

            target_cls_id = None
            
            # 🧠 暴力流核心：掃描這一行所有的欄位，看看有沒有藏著水果名字或號碼！
            for cell in row[1:]:
                cell_clean = cell.strip().lower()
                
                # 情況A：欄位直接是水果英文名字
                if cell_clean in FINAL_MAP:
                    target_cls_id = FINAL_MAP[cell_clean]
                    break
                
                # 情況B：欄位是數字 (0~8)，代表原本的種類代號
                if cell_clean.isdigit():
                    idx = int(cell_clean)
                    if idx < len(ROBO_LIST):
                        fruit_name = ROBO_LIST[idx]
                        if fruit_name in FINAL_MAP:
                            target_cls_id = FINAL_MAP[fruit_name]
                            break

            # 如果真的都找不到，預設當作 0 (Apple) 處理防止閃退
            if target_cls_id is None:
                target_cls_id = 0

            # 生成標準 YOLO 座標 (置中大框框)
            yolo_line = f"{target_cls_id} 0.5 0.5 0.8 0.8\n"

            # 穿上 csv_ 防撞新衣
            clean_base = os.path.splitext(img_name)[0]
            target_img_name = f"csv_{clean_base}.jpg"
            target_txt_name = f"csv_{clean_base}.txt"

            dst_img_path = os.path.join(new_img_dir, target_img_name)
            dst_lbl_path = os.path.join(new_lbl_dir, target_txt_name)

            # 複製照片
            shutil.copy(src_img_path, dst_img_path)
            
            # 寫入文字檔
            with open(dst_lbl_path, "a") as f_txt:
                f_txt.write(yolo_line)
            
            merge_count += 1

    # 📜 強制寫入最終版 16 種水果 data.yaml
    yaml_path = os.path.join(new_base, "data.yaml")
    with open(yaml_path, "w") as f:
        f.write(f"train: {new_base}/train/images\n")
        f.write(f"val: {new_base}/train/images\n")
        f.write("nc: 16\n")
        f.write("names: ['Apple', 'Avocado', 'Banana', 'Guava', 'Kiwi', 'Mango', 'Orange', 'Peach', 'Pineapple', 'Jackfruit', 'Litchi', 'Hog Plum', 'Papaya', 'Grapes', 'Sugerapple', 'Watermelon']\n")

    print("\n🎉🎉🎉 暴力解密合體超級成功！！！ 🎉🎉🎉")
    print(f"✅ 成功擊破 CSV 生死簿，強制搬運了 {merge_count} 組貨物進新基地！")
    print(f"📂 16種水果大滿貫黃金基地徹底完工：\n👉 {new_base}")

if __name__ == '__main__':
    main()