from flask import Flask, request, jsonify
from PIL import Image
import numpy as np
from io import BytesIO
import requests
import base64

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
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    response = requests.get(url)
    img = Image.open(BytesIO(response.content)).convert("RGB")
    regions = split_by_white_lines(img)
    results = []
    for (top, bottom) in regions:
        cropped = img.crop((0, top, img.width, bottom))
        buf = BytesIO()
        cropped.save(buf, format="PNG")
        results.append(base64.b64encode(buf.getvalue()).decode())
    return jsonify({"images": results})
