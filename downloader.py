import yt_dlp
import threading
import re

class Downloader:
    def __init__(self, progress_hooks, log_hook):
        self.progress_hooks = progress_hooks
        self.log_hook = log_hook

    def strip_ansi(self, text):
        return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

    def get_info(self, url):
        try:
            with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                return ydl.extract_info(url, download=False)
        except: return None

    def download(self, url, options):
        def run():
            ydl_opts = {
                'format': options.get('format'),
                'outtmpl': options.get('outtmpl'),
                'progress_hooks': [self.progress_hooks],
                'merge_output_format': options.get('ext', 'mp4'),
                'logger': type('Logger', (), {
                    'debug': lambda x: self.log_hook(self.strip_ansi(x)),
                    'warning': lambda x: self.log_hook(self.strip_ansi(x)),
                    'error': lambda x: self.log_hook(self.strip_ansi(x))
                }),
                'postprocessor_hooks': [self.progress_hooks] # Для отслеживания финала
            }
            if options.get('ext') == 'mp3':
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            except Exception as e:
                self.log_hook(f"Error: {str(e)}")

        threading.Thread(target=run, daemon=True).start()