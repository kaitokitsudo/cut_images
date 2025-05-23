from flask import Flask, request, jsonify
from PIL import Image
import numpy as np
from io import BytesIO
import requests

app = Flask(__name__)

def is_white_row(row, threshold=250, white_ratio=0.98):
    return np.mean(row) > threshold and (np.sum(row > threshold) / len(row)) > white_ratio

def split_by_white_lines(img, min_gap=20):
    gray = img.convert('L')
    arr = np.array(gray)
    white_rows = [y for y in range(arr.shape[0]) if is_white_row(arr[y])]
    cuts, regions = [], []
    if not white_rows:
        return []
    current = [white_rows[0]]
    for y in white_rows[1:]:
        if y - current[-1] <= min_gap:
            current.append(y)
        else:
            cuts.append((current[0], current[-1]))
            current = [y]
    cuts.append((current[0], current[-1]))
    start = 0
    for (top, bottom) in cuts:
        if top - start > 20:
            regions.append((start, top))
        start = bottom
    if img.height - start > 20:
        regions.append((start, img.height))
    return regions

@app.route("/cut", methods=["POST"])
def cut_image():
    data = request.json
    url = data.get("url")
    access_token = data.get("access_token")
    page_id = data.get("page_id")
    if not url or not access_token or not page_id:
        return jsonify({"error": "Missing url, access_token or page_id"}), 400

    response = requests.get(url)
    img = Image.open(BytesIO(response.content)).convert("RGB")
    regions = split_by_white_lines(img)

    uploaded_media_ids = []
    for (top, bottom) in regions:
        height = bottom - top
        if height < 300:
            continue  # bỏ qua ảnh thấp hơn 300px
            
        cropped = img.crop((0, top, img.width, bottom))
        buffered = BytesIO()
        cropped.save(buffered, format="JPEG", quality=80)
        buffered.seek(0)

        files = {
            'source': ('image.jpg', buffered, 'image/jpeg')
        }
        payload = {
            'access_token': access_token,
            'published': 'false'  # chỉ upload, không đăng ngay
        }
        upload_url = f'https://graph.facebook.com/{page_id}/photos'
        resp = requests.post(upload_url, files=files, data=payload)
        resp_json = resp.json()
        if 'id' in resp_json:
            uploaded_media_ids.append(resp_json['id'])
        else:
            return jsonify({"error": "Upload failed", "details": resp_json}), 500

    attached_media = [{"media_fbid": media_id} for media_id in uploaded_media_ids]
    return jsonify({"attached_media": attached_media})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
