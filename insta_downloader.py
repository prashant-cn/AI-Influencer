import os
import datetime
import subprocess
import logging
import time
import requests

from pathlib import Path

import instaloader
import yt_dlp


class InstagramReelDownloader:

    def __init__(
        self,
        handles,
        base_download_folder="downloads",
        shorts_folder="shorts",
        date_limit="20240101"
    ):

        self.handles = handles
        self.base_download_folder = Path(base_download_folder)
        self.shorts_folder = Path(shorts_folder)
        self.date_limit = datetime.datetime.strptime(date_limit, "%Y%m%d")

        self.base_download_folder.mkdir(exist_ok=True)
        self.shorts_folder.mkdir(exist_ok=True)

        self._setup_logging()

        # Instaloader instance (NO downloading)
        self.loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            save_metadata=False,
            compress_json=False,
        )

    # ================= LOGGING ================= #

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler("instagram_downloader.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger()

    # ================= NVENC ================= #

    def _convert_to_shorts_nvenc(self, input_path, handle):

        filename = Path(input_path).name
        handle_shorts_folder = self.shorts_folder / handle
        handle_shorts_folder.mkdir(exist_ok=True)

        output_path = handle_shorts_folder / filename

        cmd = [
            "ffmpeg",
            "-y",
            "-i", input_path,
            "-t", "60",
            "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
            "-c:v", "h264_nvenc",
            "-preset", "p4",
            "-rc", "vbr",
            "-cq", "23",
            "-b:v", "0",
            "-c:a", "aac",
            str(output_path)
        ]

        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return str(output_path)

    #============caption and cover===========
    def _save_caption_file(self, handle_folder, shortcode, caption):
        txt_path = handle_folder / f"{shortcode}.txt"

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(caption if caption else "")

        return txt_path

    def _download_cover_image(self, handle_folder, shortcode, cover_url):
        cover_path = handle_folder / f"{shortcode}_cover.jpg"

        try:
            response = requests.get(cover_url, timeout=15)
            if response.status_code == 200:
                with open(cover_path, "wb") as f:
                    f.write(response.content)
        except Exception as e:
            self.logger.error(f"Cover download failed: {e}")

        return cover_path


    # ================= MAIN ================= #

    def _process_handle(self, handle):

        self.logger.info(f"Processing @{handle}")

        handle_folder = self.base_download_folder / handle
        handle_folder.mkdir(exist_ok=True)

        archive_file = handle_folder / "archive.txt"

        profile = instaloader.Profile.from_username(self.loader.context, handle)

        for post in profile.get_posts():

            # Only Reels
            if post.typename != "GraphVideo":
                continue

            # Date filter
            if post.date < self.date_limit:
                continue

            reel_url = f"https://www.instagram.com/p/{post.shortcode}/"
            shortcode = post.shortcode
            caption = post.caption
            cover_url = post.url  # thumbnail image


            self.logger.info(f"Downloading Reel: {reel_url}")

            ydl_opts = {
                'outtmpl': f'{handle_folder}/%(id)s.%(ext)s',
                'download_archive': str(archive_file),

                # Best quality
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',

                # Stability
                'retries': 10,
                'fragment_retries': 10,
                'sleep_interval': 2,
                'max_sleep_interval': 5,
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    result = ydl.extract_info(reel_url, download=True)

                    if not result:
                        continue

                    file_path = ydl.prepare_filename(result)

                    if not file_path.endswith(".mp4"):
                        file_path = str(Path(file_path).with_suffix(".mp4"))

                    shorts_path = self._convert_to_shorts_nvenc(file_path, handle)
                    # Save caption
                    self._save_caption_file(handle_folder, shortcode, caption)
                    # Download cover image
                    self._download_cover_image(handle_folder, shortcode, cover_url)

                    self.logger.info(f"Short created: {shorts_path}")
                    time.sleep(2)

            except Exception as e:
                self.logger.error(f"Error processing reel: {e}")
                continue

    # ================= RUN ================= #

    def run(self):
        for handle in self.handles:
            try:
                self._process_handle(handle)
            except KeyboardInterrupt:
                self.logger.warning("Stopped manually.")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error for {handle}: {e}")
                continue


# ================= ENTRY ================= #

if __name__ == "__main__":

    HANDLES = [
        # "your_shreyarao",
        # "stephanieh.be",
        # "itsbabytana",
        # "its_saahana"
        # "ale_kost",
        "financewithanubhav_",
        # "rubytakesyourheart"
    ]

    downloader = InstagramReelDownloader(
        handles=HANDLES,
        date_limit="20260101"
    )

    downloader.run()
