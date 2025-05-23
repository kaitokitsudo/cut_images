import requests
from io import BytesIO
from PIL import Image
import numpy as np

def split_images_from_urls(urls, threshold=245, min_gap=30, min_crop_height=300):
    blobs = []
    global_index = 1

    for url in urls:
        try:
            response = requests.get(url)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content))

            gray = image.convert("L")
            arr = np.array(gray)

            white_rows = []
            for i, row in enumerate(arr):
                if np.mean(row) > threshold:
                    white_rows.append(i)

            cuts = []
            last = -min_gap
            for i in white_rows:
                if i - last >= min_gap:
                    cuts.append(i)
                    last = i

            cuts = [0] + cuts + [arr.shape[0]]

            for idx in range(len(cuts) - 1):
                top, bottom = cuts[idx], cuts[idx + 1]
                height = bottom - top

                # ❌ Bỏ qua phần ảnh cắt có chiều cao nhỏ hơn yêu cầu
                if height < min_crop_height:
                    print(f"⚠️  Bỏ phần cắt {idx} từ {url} vì chiều cao {height}px < {min_crop_height}px")
                    continue

                crop = image.crop((0, top, image.width, bottom))

                blob_io = BytesIO()
                crop.save(blob_io, format="JPEG")
                blob_io.seek(0)

                blobs.append(blob_io)
                global_index += 1

            print(f"✅ Đã chia ảnh {url} thành {len(blobs)} phần hợp lệ.")
        except Exception as e:
            print(f"❌ Lỗi với ảnh {url}: {e}")

    return blobs
