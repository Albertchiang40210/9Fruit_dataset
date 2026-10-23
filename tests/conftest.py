import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("API_KEY", "test-key")


class _FakeYOLO:
    names = {0: "apple"}

    def __init__(self, *a, **k):
        pass

    def to(self, *a, **k):
        return self


# 測試不需要真的載入模型
fake = types.ModuleType("ultralytics")
fake.YOLO = _FakeYOLO
sys.modules.setdefault("ultralytics", fake)
