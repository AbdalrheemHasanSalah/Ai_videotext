from flask import Flask, request, jsonify, render_template
import cv2
import os
import pytesseract
from pathlib import Path
import shutil
import subprocess

app = Flask(__name__)

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

YTDLP_PATH = r'C:\Users\abdsa\AppData\Local\Programs\Python\Python313\Scripts\yt-dlp.exe'

def download_video(url, filename='downloads/video.mp4'):
    os.makedirs('downloads', exist_ok=True)

    if os.path.exists(filename):
        os.remove(filename)

    command = [
        YTDLP_PATH,
        '-f', 'bestvideo[ext=mp4]',
        '-o', filename,
        url
    ]

    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if result.returncode != 0:
       print("❌ YT-DLP STDERR:", result.stderr)
       raise RuntimeError("Download failed. Try running terminal as administrator.")


    return filename

def extract_frames(video_path, folder='frames', interval_sec=1):
    Path(folder).mkdir(parents=True, exist_ok=True)
    vid = cv2.VideoCapture(video_path)
    fps = vid.get(cv2.CAP_PROP_FPS)
    count = 0
    frame_number = 0
    while True:
        ret, frame = vid.read()
        if not ret:
            break
        if int(frame_number % (fps * interval_sec)) == 0:
            cv2.imwrite(os.path.join(folder, f"frame{count}.jpg"), frame)
            count += 1
        frame_number += 1
    vid.release()
    return folder

def extract_text_from_frames(folder):
    results = {}
    for file in sorted(os.listdir(folder)):
        if file.endswith('.jpg'):
            path = os.path.join(folder, file)
            text = pytesseract.image_to_string(path, lang='ara+eng').strip()
            if text:
                results[file] = text
    return results

def cleanup(files_and_dirs):
    for path in files_and_dirs:
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/extract-text', methods=['POST'])
def extract_text():
    try:
        data = request.get_json(force=True)
        print("🔎 Received data:", data)
        url = data.get('url')
        if not url:
            return jsonify({'error': 'Missing YouTube URL'}), 400
    except Exception as e:
        return jsonify({'error': f'Invalid JSON format: {e}'}), 400

    try:
        video_path = download_video(url)
        frames_folder = extract_frames(video_path)
        text_results = extract_text_from_frames(frames_folder)

        cleanup([video_path, frames_folder])

        return jsonify(text_results)
    except Exception as e:
        print("❌ Server Exception:", e)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
