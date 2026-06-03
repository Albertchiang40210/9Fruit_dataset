from ultralytics import YOLO

def main():
    # 🚀 關鍵修正：指名道姓叫出 2026 最新中型大腦 "yolo26m.pt"
    # 系統等一下會自動幫你下載這顆最新的官方模型！
    model = YOLO("yolo26m.pt")

    # 🔥 點火特訓開始！大腦正式進入黃金房間修練
    print("🛸 最新 2026 中型大腦 yolo26m 二次超級進化開始點火...")
    model.train(
        data="data.yaml",   # 📄 點名 23 種萬物同學的點名簿
        epochs=50,          # 🔄 總共苦讀 + 模擬考 50 輪
        imgsz=640,          # 📐 照片解析度鎖定 640x640 最準
        device="mps"        # ⚡ 叫阿伯的 Mac M系列晶片全力加速運算
    )
    print("🎉 恭喜阿伯！yolo26m 50輪特訓全部大功告成！")

if __name__ == '__main__':
    main()