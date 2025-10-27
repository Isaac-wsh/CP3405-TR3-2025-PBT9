# test_client.py
# 简介：命令行测试后端接口的小脚本。
# 用法：python test_client.py <image_path>
# 依赖：requests ；安装：pip install requests

import sys
import requests

URL = "http://127.0.0.1:8000/api/check_seat"

def main():
    if len(sys.argv) < 2:
        print("用法: python test_client.py <image_path>")
        sys.exit(1)
    img_path = sys.argv[1]
    with open(img_path, "rb") as f:
        files = {"file": (img_path, f, "image/jpeg")}
        r = requests.post(URL, files=files, timeout=60)
    print(r.status_code, r.json())

if __name__ == "__main__":
    main()
