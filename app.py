import os, requests
from flask import Flask, request, Response, send_from_directory

# Keys hardcoded as fallback -- Railway env vars take priority
TRIPO_KEY    = os.environ.get("TRIPO_KEY",    "tsk_qK6hrDAEG3QY6q5-Qhx8WgYPj0VyILl-ZXEL57lniZP")
REMOVEBG_KEY = os.environ.get("REMOVEBG_KEY", "adDVRJDxsJ4g6SZXg8Dy4FSN")
TRIPO_BASE   = "https://api.tripo3d.ai"

app = Flask(__name__, static_folder="static", static_url_path="")

def cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp

@app.route("/proxy/removebg", methods=["POST","OPTIONS"])
def removebg():
    if request.method == "OPTIONS":
        return cors(Response("", 200))
    file_items = list(request.files.items())
    if not file_items:
        return cors(Response('{"error":"no file"}', 400))
    name, f = file_items[0]
    resp = requests.post(
        "https://api.remove.bg/v1.0/removebg",
        headers={"X-Api-Key": REMOVEBG_KEY},
        files={"image_file": (f.filename, f.read(), f.content_type)},
        data={"size": "auto", "type": "animal"}, timeout=30)
    if resp.status_code == 200:
        import base64
        b64 = base64.b64encode(resp.content).decode()
        return cors(Response(f'{{"data_url":"data:image/png;base64,{b64}"}}',
                             200, {"Content-Type": "application/json"}))
    return cors(Response(resp.text, resp.status_code, {"Content-Type": "application/json"}))

@app.route("/glb-proxy")
def glb_proxy():
    url = request.args.get("url", "")
    if not url or "tripo-data" not in url:
        return cors(Response('{"error":"invalid url"}', 400))
    try:
        resp = requests.get(url, timeout=60, stream=True)
        return cors(Response(resp.iter_content(chunk_size=8192),
                             resp.status_code, {"Content-Type": "model/gltf-binary"}))
    except Exception as e:
        return cors(Response(f'{{"error":"{str(e)}"}}', 502))

@app.route("/proxy/<path:path>", methods=["GET","POST","OPTIONS"])
def proxy(path):
    if request.method == "OPTIONS":
        return cors(Response("", 200))
    url = f"{TRIPO_BASE}/{path}"
    headers = {"Authorization": f"Bearer {TRIPO_KEY}"}
    if request.content_type and "multipart" in request.content_type:
        files = {name: (f.filename, f.read(), f.content_type)
                 for name, f in request.files.items()}
        resp = requests.post(url, headers=headers, files=files, timeout=120)
    else:
        resp = requests.request(request.method, url,
            headers={**headers, "Content-Type": "application/json"},
            data=request.get_data(), timeout=120)
    return cors(Response(resp.content, resp.status_code, {"Content-Type": "application/json"}))

@app.route("/")
def index():
    resp = send_from_directory("static", "index.html")
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8765)))
