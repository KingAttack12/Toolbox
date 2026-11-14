"""Real file conversions with isolated storage, plus hostile/oversized input checks."""
import io
import json
import shutil
from pathlib import Path
import subprocess
import tempfile
import unittest
import wave
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont
import pymupdf
from docx import Document

from app import accounts, auth, config, workload
from app.routers import tools_image, tools_media, tools_office


class MoreConversionsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.patches = [patch.object(accounts, 'DB_PATH', self.root / 'accounts.sqlite3'),
                        patch.object(config, 'DATA_DIR', self.root / 'jobs'),
                        patch.object(config, 'USERNAME', 'owner'),
                        patch.object(workload, 'workload', workload.Workload()),
                        patch.object(auth, '_sessions', {})]
        for item in self.patches: item.start()
        app = FastAPI()
        for router in (tools_image.router, tools_media.router, tools_office.router): app.include_router(router)
        self.client = TestClient(app, base_url='https://testserver')
        self.client.cookies.set(config.SESSION_COOKIE, auth.create_session('owner'))

    def tearDown(self):
        self.client.close()
        for item in reversed(self.patches): item.stop()
        self.temp.cleanup()

    def post(self, route, data, format=None):
        return self.client.post('/api/tools/' + route, files={'file': ('input.bin', data)}, data={'format': format} if format else {})

    def image(self):
        buffer = io.BytesIO()
        image = Image.new('RGB', (1000, 180), 'white')
        font_path = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
        font = ImageFont.truetype(str(font_path), 50) if font_path.exists() else ImageFont.load_default(size=50)
        ImageDraw.Draw(image).text((20, 50), 'Toolbox conversion test', fill='black', font=font)
        image.save(buffer, format='PNG')
        return buffer.getvalue()

    def test_image_formats_and_ico(self):
        for format, expected in [('bmp', 'BMP'), ('tiff', 'TIFF'), ('gif', 'GIF'), ('ico', 'ICO')]:
            with self.subTest(format=format):
                result = self.post('image/convert', self.image(), format)
                self.assertEqual(result.status_code, 200, result.text[:100] if result.status_code != 200 else '')
                with Image.open(io.BytesIO(result.content)) as image: self.assertEqual(image.format, expected)
        self.assertEqual(self.post('image/convert', b'<svg/>', 'png').status_code, 400)
        self.assertEqual(self.post('image/convert', self.image(), 'svg').status_code, 422)

    @unittest.skipUnless(shutil.which('tesseract'), 'Tesseract requis')
    def test_image_ocr(self):
        result = self.post('office/image-ocr', self.image())
        if result.status_code == 501: self.skipTest('Langues OCR français et anglais requises')
        self.assertEqual(result.status_code, 200)
        self.assertIn('Toolbox', result.text)

    def test_pdf_and_word_text(self):
        with pymupdf.open() as document:
            page = document.new_page()
            page.insert_text((50, 50), 'Toolbox direct text')
            data = document.tobytes()
        result = self.post('office/pdf-text', data)
        self.assertEqual(result.status_code, 200)
        self.assertIn('Toolbox direct text', result.text)
        with pymupdf.open() as document:
            document.new_page()
            self.assertEqual(self.post('office/pdf-text', document.tobytes()).status_code, 422)
        document = Document()
        document.add_paragraph('Première ligne avec accents')
        document.add_paragraph('Deuxième ligne')
        buffer = io.BytesIO(); document.save(buffer)
        result = self.post('office/word-text', buffer.getvalue())
        self.assertEqual(result.status_code, 200)
        self.assertIn('Première ligne avec accents\nDeuxième ligne', result.text)
        self.assertEqual(self.post('office/word-text', b'not docx').status_code, 400)

    def wav(self):
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as audio:
            audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(8000); audio.writeframes(b'\0\0' * 4000)
        return buffer.getvalue()

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg et ffprobe requis')
    def test_all_audio_formats_and_roundtrip(self):
        for format in ('mp3', 'wav', 'flac', 'ogg', 'm4a'):
            with self.subTest(format=format):
                result = self.post('media/convert', self.wav(), format)
                self.assertEqual(result.status_code, 200, result.text[:100] if result.status_code != 200 else '')
                self.assertGreater(len(result.content), 100)
                decoded = self.post('media/convert', result.content, 'wav')
                self.assertEqual(decoded.status_code, 200)
                with wave.open(io.BytesIO(decoded.content)) as audio: self.assertGreater(audio.getnframes(), 0)

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg et ffprobe requis')
    def test_video_outputs_and_missing_audio(self):
        source = self.root / 'source.mp4'
        subprocess.run([tools_media._ffmpeg_bin(), '-v', 'error', '-f', 'lavfi', '-i', 'color=c=blue:s=160x120:r=10', '-t', '0.5', '-c:v', 'libx264', '-threads', '1', str(source)], check=True, timeout=20)
        data = source.read_bytes()
        for format in ('mp4', 'webm'):
            result = self.post('media/convert', data, format)
            self.assertEqual(result.status_code, 200, result.text[:100] if result.status_code != 200 else '')
            target = self.root / ('result.' + format); target.write_bytes(result.content)
            info = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(target)], timeout=10))
            video = next(stream for stream in info['streams'] if stream['codec_type'] == 'video')
            self.assertLessEqual(video['width'], 1280); self.assertLessEqual(video['height'], 720)
        self.assertEqual(self.post('media/convert', data, 'mp3').status_code, 400)

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg et ffprobe requis')
    def test_media_limits_invalid_uploads_and_auth(self):
        self.assertEqual(self.post('media/convert', b'#EXTM3U\nfile:///etc/passwd', 'mp3').status_code, 400)
        self.assertEqual(self.post('media/convert', b'', 'wav').status_code, 400)
        self.assertEqual(self.post('media/convert', self.wav(), 'exe').status_code, 422)
        with patch.object(tools_media, 'MAX_FILESIZE', 10):
            self.assertEqual(self.post('media/convert', self.wav(), 'wav').status_code, 413)
        with patch('subprocess.run') as run:
            run.return_value.stdout = json.dumps({'format': {'duration': '601'}}).encode()
            self.assertEqual(self.post('media/convert', self.wav(), 'mp3').status_code, 400)
            self.assertEqual(run.call_count, 1)
        self.client.cookies.clear()
        self.assertEqual(self.post('media/convert', self.wav(), 'mp3').status_code, 401)
