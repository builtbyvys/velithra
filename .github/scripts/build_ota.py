#!/usr/bin/env python3

import hashlib
import json
import os
import urllib.parse

import requests
from bs4 import BeautifulSoup

DEVICE = "cheetah"
BUILD_PREFIX = "TQ"
GOOGLE_OTA_URL = "https://developers.google.com/android/ota"


def fetch_ota():
    response = requests.get(GOOGLE_OTA_URL)
    soup = BeautifulSoup(response.text, "html.parser")

    ota_links = []
    for link in soup.find_all("a"):
        href = link.get("href")
        if href and DEVICE in href and href.endswith(".zip") and BUILD_PREFIX in href:
            ota_links.append(href)

    return ota_links


def get_latest():
    try:
        with open("./site/root/metadata.json", "r") as f:
            metadata = json.load(f)
            return metadata.get("current_build", "")
    except (FileNotFoundError, json.JSONDecodeError):
        try:
            with open("./site/metadata.json", "r") as f:
                metadata = json.load(f)
                return metadata.get("current_build", "")
        except (FileNotFoundError, json.JSONDecodeError):
            return ""


def download_file(url, output_path):
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get("content-length", 0))

    with open(output_path, "wb") as f:
        downloaded = 0
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                percent = int(downloaded / total_size * 100)
                if total_size > 0:
                    print(
                        f"Downloaded: {percent}% ({downloaded}/{total_size})", end="\r"
                    )

    print(f"\nDownload complete: {output_path}")
    return output_path


def calc_sha256(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def main():
    os.makedirs("./site", exist_ok=True)

    current_build = get_latest()

    ota_links = fetch_ota()
    if not ota_links:
        print("No OTA links found for device:", DEVICE)
        return

    ota_links.sort(reverse=True)
    latest_ota_url = ota_links[0]

    build = urllib.parse.unquote(latest_ota_url.split("/")[-1]).split("-")[1]

    if build == current_build:
        print(f"Already processed latest build {build}. Nothing to do.")
        return

    print(f"Found new build: {build}")
    print(f"Downloading OTA from: {latest_ota_url}")

    download_file(latest_ota_url, "./ota.zip")

    sha256 = calc_sha256("./ota.zip")
    print(f"SHA256: {sha256}")

    with open("./ota_source.json", "w") as f:
        json.dump(
            {"build": build, "url": latest_ota_url, "sha256": sha256}, f, indent=2
        )

    print("OTA download complete and ready for processing")


if __name__ == "__main__":
    main()
