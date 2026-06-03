import os
from ultralytics import YOLO

def main():
    # 👑 召喚你剛剛熱騰騰練出來的 YOLO26 水果神腦！
    # 注意：YOLO 訓練完最聰明的權重會自動存放在這裡，如果等一下資料夾名稱有變，我們再微調
    model = YOLO('/Users/albert/Documents/Fruit classification dataset/result/train-7/weights/best.pt')
    
    print("🚀 YOLO26 水果神腦已成功裝載！準備開始期末考...")

    # 考卷路徑：直接吃你上一批下載、放在新相簿大盒子裡的 train 照片
    # 這樣它就能在完全沒有標籤檔的提示下，自己嘗試去畫框！
    source_images = "images/train" 

    # 開始推論畫框！
    # save=True 代表讓 AI 自動幫你把畫好框的彩色成果照片存下來
    model.predict(source=source_images, save=True, imgsz=640, device="mps")
    
    print("🎉 期末考結束！彩色畫框水果照片已存放在 runs/detect/predict 資料夾中！")

if __name__ == "__main__":
    main()