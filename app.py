from flask import Flask, request, jsonify, render_template
import cv2
import os
import pytesseract
from pathlib import Path
import shutil
import subprocess

app = Flask(__name__)

# تأكد تعديل المسار بما يناسب جهازك ويندوز
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# مسار yt-dlp.exe على ويندوز - عدّل حسب مكان تثبيت yt-dlp على جهازك
YTDLP_PATH = r'C:\Users\abdsa\AppData\Local\Programs\Python\Python313\Scripts\yt-dlp.exe'


def download_video(url, filename='downloads\\video.mp4'):
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
       raise RuntimeError("Download failed. حاول تشغيل VSCode كمسؤول (Run as Administrator).")

    return filename


def extract_frames(video_path, folder='frames', interval_sec=3):
    Path(folder).mkdir(parents=True, exist_ok=True)
    vid = cv2.VideoCapture(video_path)
    fps = vid.get(cv2.CAP_PROP_FPS)
    total_frames = int(vid.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"🎬 Video info: {fps} FPS, {total_frames} total frames")

    count = 0
    frame_number = 0
    while True:
        ret, frame = vid.read()
        if not ret:
            break
        if int(frame_number % (fps * interval_sec)) == 0:
            cv2.imwrite(os.path.join(folder, f"frame{count}.jpg"), frame)
            count += 1
            if count % 10 == 0:
                print(f"📸 Extracted {count} frames...")
        frame_number += 1
    vid.release()
    print(f"✅ Extracted {count} frames total")
    return folder


def extract_text_from_frames(folder):
    results = {}
    files = [f for f in sorted(os.listdir(folder)) if f.endswith('.jpg')]
    total_files = len(files)

    print(f"🔍 Starting OCR on {total_files} frames...")

    for i, file in enumerate(files, 1):
        path = os.path.join(folder, file)
        text = pytesseract.image_to_string(path, lang='ara+eng').strip()
        if text:
            results[file] = text

        if i % 10 == 0 or i == total_files:
            print(f"📝 OCR progress: {i}/{total_files} frames processed")

    print(f"✅ OCR complete! Found text in {len(results)} frames")
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
    video_path = None
    frames_folder = None

    try:
        data = request.get_json(force=True)
        print("🔎 Received data:", data)
        url = data.get('url')
        if not url:
            return jsonify({'error': 'Missing YouTube URL'}), 400
    except Exception as e:
        return jsonify({'error': f'Invalid JSON format: {e}'}), 400

    try:
        print("📥 Starting video download...")
        video_path = download_video(url)
        print("✅ Video downloaded successfully")

        print("🎬 Extracting frames...")
        frames_folder = extract_frames(video_path)

        print("🔍 Running OCR on frames...")
        text_results = extract_text_from_frames(frames_folder)

        return jsonify(text_results)

    except Exception as e:
        print("❌ Server Exception:", e)
        return jsonify({'error': str(e)}), 500

    finally:
        cleanup_files = []
        if video_path and os.path.exists(video_path):
            cleanup_files.append(video_path)
        if frames_folder and os.path.exists(frames_folder):
            cleanup_files.append(frames_folder)

        if cleanup_files:
            print("🧹 Cleaning up temporary files...")
            cleanup(cleanup_files)
            print("✅ Cleanup complete! Files deleted.")
        else:
            print("ℹ️ No files to clean up.")


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
