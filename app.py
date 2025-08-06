
from flask import Flask, request, jsonify, render_template
import cv2
import os
import pytesseract
from pathlib import Path
import shutil
import subprocess
import platform

app = Flask(__name__)

def find_tesseract_windows():
    """Search for tesseract.exe in Windows file system"""
    import glob
    
    print("🔍 Searching for Tesseract on Windows...")
    
    # First try PATH
    try:
        result = subprocess.run(['tesseract', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ Found Tesseract in PATH")
            return 'tesseract'
    except:
        pass
    
    # Search common installation directories
    search_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        r'C:\Users\*\AppData\Local\Tesseract-OCR\tesseract.exe',
        r'C:\Users\*\AppData\Local\Programs\Tesseract-OCR\tesseract.exe',
        r'C:\ProgramData\Tesseract-OCR\tesseract.exe',
        r'C:\Tesseract-OCR\tesseract.exe',
        r'D:\Program Files\Tesseract-OCR\tesseract.exe',
        r'D:\Program Files (x86)\Tesseract-OCR\tesseract.exe'
    ]
    
    for pattern in search_paths:
        matches = glob.glob(pattern)
        for path in matches:
            if os.path.exists(path):
                try:
                    # Test if tesseract works
                    result = subprocess.run([path, '--version'], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        print(f"✅ Found working Tesseract at: {path}")
                        return path
                except:
                    continue
    
    # If not found in common paths, search entire C: drive (can be slow but thorough)
    print("🔍 Searching entire C: drive for tesseract.exe (this may take a moment)...")
    try:
        for root, dirs, files in os.walk('C:\\'):
            if 'tesseract.exe' in files:
                path = os.path.join(root, 'tesseract.exe')
                try:
                    result = subprocess.run([path, '--version'], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        print(f"✅ Found working Tesseract at: {path}")
                        return path
                except:
                    continue
            # Skip some directories to speed up search
            dirs[:] = [d for d in dirs if not d.startswith(('Windows', 'System', '$'))]
    except Exception as e:
        print(f"⚠️ Error during file system search: {e}")
    
    return None

# Configure tesseract based on operating system
if platform.system() == "Windows":
    tesseract_path = find_tesseract_windows()
    
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        print(f"✅ Tesseract configured: {tesseract_path}")
    else:
        print("❌ Tesseract not found on Windows. Please install it from: https://github.com/UB-Mannheim/tesseract/wiki")
        print("   Or ensure it's added to your system PATH")

# For Linux/Mac, tesseract should be available in PATH
# No need to set tesseract_cmd on Unix-like systems

# Use yt-dlp command that works cross-platform
def get_ytdlp_command():
    """Get the appropriate yt-dlp command for the current system"""
    
    # Try Python module method first (most reliable and doesn't require elevation)
    try:
        result = subprocess.run([
            'python', '-m', 'yt_dlp', '--version'
        ], capture_output=True, check=True, text=True, timeout=10)
        print("✅ Using Python module: python -m yt_dlp")
        return ['python', '-m', 'yt_dlp']
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"⚠️ Python module method failed: {e}")
    
    # Try sys.executable (current Python interpreter) with yt-dlp module
    try:
        import sys
        result = subprocess.run([
            sys.executable, '-m', 'yt_dlp', '--version'
        ], capture_output=True, check=True, text=True, timeout=10)
        print(f"✅ Using sys.executable: {sys.executable} -m yt_dlp")
        return [sys.executable, '-m', 'yt_dlp']
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"⚠️ sys.executable method failed: {e}")
    
    # Try the simple command that should work if yt-dlp is in PATH
    try:
        result = subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True, text=True, timeout=10)
        print("✅ Using direct command: yt-dlp")
        return ['yt-dlp']
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"⚠️ Direct yt-dlp command failed: {e}")
    
    # On Windows, try to find yt-dlp.exe in common locations
    if platform.system() == "Windows":
        import shutil
        
        # Try using shutil.which to find yt-dlp
        ytdlp_path = shutil.which('yt-dlp')
        if ytdlp_path:
            try:
                result = subprocess.run([ytdlp_path, '--version'], capture_output=True, check=True, text=True, timeout=10)
                print(f"✅ Found yt-dlp using shutil.which: {ytdlp_path}")
                return [ytdlp_path]
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
                print(f"⚠️ shutil.which found path but failed: {e}")
        
        # Try the .exe version explicitly
        try:
            result = subprocess.run(['yt-dlp.exe', '--version'], capture_output=True, check=True, text=True, timeout=10)
            print("✅ Using Windows executable: yt-dlp.exe")
            return ['yt-dlp.exe']
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            print(f"⚠️ Windows executable failed: {e}")
    
    # If all methods fail, provide detailed error
    error_msg = (
        "yt-dlp not found or not accessible. Please try:\n"
        "1. pip install --user yt-dlp\n"
        "2. pip install --upgrade yt-dlp\n"
        "3. Restart your terminal/IDE after installation"
    )
    raise RuntimeError(error_msg)

# Initialize yt-dlp command
try:
    YTDLP_PATH = get_ytdlp_command()
except RuntimeError as e:
    print(f"❌ {e}")
    YTDLP_PATH = None


def get_video_duration(url):
    """Get video duration in seconds using yt-dlp"""
    if YTDLP_PATH is None:
        raise RuntimeError("yt-dlp is not properly configured")
    
    command = YTDLP_PATH + ['--get-duration', '--no-download', url]
    
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    if result.returncode != 0:
        print(f"❌ yt-dlp error: {result.stderr}")
        return None
    
    duration_str = result.stdout.strip()
    
    # Parse duration (format: HH:MM:SS or MM:SS)
    try:
        parts = duration_str.split(':')
        if len(parts) == 3:  # HH:MM:SS
            hours, minutes, seconds = map(int, parts)
            return hours * 3600 + minutes * 60 + seconds
        elif len(parts) == 2:  # MM:SS
            minutes, seconds = map(int, parts)
            return minutes * 60 + seconds
        else:
            return int(parts[0])  # Just seconds
    except:
        return None


def calculate_processing_times(duration_seconds):
    """Calculate estimated processing times based on video duration"""
    if not duration_seconds:
        return {
            'download': 60,
            'frames': 120,
            'ocr': 300,
            'total': 480
        }
    
    # Base times (in seconds) for a 1-minute video
    base_download = 30
    base_frames = 45
    base_ocr_per_frame = 2  # seconds per frame for OCR
    
    # Scale factors
    duration_minutes = duration_seconds / 60
    
    # Download time scales slower (network is the bottleneck)
    download_time = base_download + (duration_minutes * 15)
    
    # Frame extraction scales almost linearly
    frames_time = base_frames + (duration_minutes * 30)
    
    # OCR time depends on number of frames (every 3 seconds = duration/3 frames)
    estimated_frames = max(1, duration_seconds // 3)
    ocr_time = estimated_frames * base_ocr_per_frame
    
    total_time = download_time + frames_time + ocr_time
    
    return {
        'download': int(download_time),
        'frames': int(frames_time),
        'ocr': int(ocr_time),
        'total': int(total_time),
        'duration': duration_seconds,
        'estimated_frames': estimated_frames
    }


def download_video(url, filename=None):
    """Download video with cross-platform path handling"""
    if YTDLP_PATH is None:
        raise RuntimeError("yt-dlp is not properly configured. Please install it: pip install yt-dlp")
    
    if filename is None:
        filename = os.path.join('downloads', 'video.mp4')
    
    os.makedirs('downloads', exist_ok=True)

    # Clean up any existing files including partial downloads
    cleanup_patterns = [
        filename,
        filename + '.part',
        filename + '.ytdl',
        filename + '.part-Frag*.part'
    ]
    
    for pattern in cleanup_patterns:
        if '*' in pattern:
            # Handle wildcard patterns
            import glob
            for file_path in glob.glob(pattern):
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        print(f"🧹 Removed partial file: {file_path}")
                    except:
                        pass
        else:
            if os.path.exists(pattern):
                try:
                    os.remove(pattern)
                    print(f"🧹 Removed existing file: {pattern}")
                except:
                    pass

    # Enhanced command with options to prevent resume issues
    command = YTDLP_PATH + [
        '-f', 'bestvideo[ext=mp4]/best[ext=mp4]/best',  # More flexible format selection
        '--no-part',                    # Don't use .part files
        '--no-continue',                # Don't resume partial downloads
        '--retries', '3',               # Retry failed downloads
        '--fragment-retries', '3',      # Retry failed fragments
        '--abort-on-unavailable-fragment',  # Abort if fragments fail
        '--prefer-free-formats',        # Prefer formats that don't require special handling
        '-o', filename,
        url
    ]

    print(f"🔄 Download command: {' '.join(command)}")
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if result.returncode != 0:
       print("❌ YT-DLP STDERR:", result.stderr)
       print("❌ YT-DLP STDOUT:", result.stdout)
       
       # Try alternative approach if the main download fails
       print("🔄 Trying alternative download method...")
       alt_command = YTDLP_PATH + [
           '-f', 'worst[ext=mp4]/worst',  # Use lower quality as fallback
           '--no-part',
           '--no-continue',
           '-o', filename,
           url
       ]
       
       alt_result = subprocess.run(alt_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
       
       if alt_result.returncode != 0:
           raise RuntimeError(f"Download failed with both methods. Primary error: {result.stderr}. Alternative error: {alt_result.stderr}")
       else:
           print("✅ Alternative download method succeeded")

    if not os.path.exists(filename):
        raise RuntimeError("Download completed but video file not found")

    print(f"✅ Video downloaded: {filename} ({os.path.getsize(filename)} bytes)")
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


@app.route('/get-video-info', methods=['POST'])
def get_video_info():
    try:
        data = request.get_json(force=True)
        url = data.get('url')
        if not url:
            return jsonify({'error': 'Missing YouTube URL'}), 400
        
        print(f"🔍 Getting video duration for: {url}")
        duration = get_video_duration(url)
        
        if duration is None:
            return jsonify({'error': 'Could not get video information'}), 400
        
        processing_times = calculate_processing_times(duration)
        
        # Format duration for display
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        seconds = duration % 60
        
        if hours > 0:
            duration_str = f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            duration_str = f"{minutes}m {seconds}s"
        else:
            duration_str = f"{seconds}s"
        
        return jsonify({
            'duration': duration,
            'duration_formatted': duration_str,
            'processing_times': processing_times
        })
        
    except Exception as e:
        print(f"❌ Error getting video info: {e}")
        return jsonify({'error': str(e)}), 500


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
    app.run(host='0.0.0.0', port=5000, debug=True)
