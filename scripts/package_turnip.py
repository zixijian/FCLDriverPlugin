#!/usr/bin/env python3
"""
Helper script to fetch Turnip drivers from StevenMXZ/Adreno-Tools-Drivers releases
and package each Turnip driver into an FCL driver APK.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

UPSTREAM_REPO = "StevenMXZ/Adreno-Tools-Drivers"
GITHUB_API_RELEASES = f"https://api.github.com/repos/{UPSTREAM_REPO}/releases"


def get_headers():
    token = os.environ.get("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "FCL-Driver-Builder"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_json(url):
    req = urllib.request.Request(url, headers=get_headers())
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def find_latest_turnip_release():
    """Find the latest release containing at least one turnip zip asset."""
    releases = fetch_json(GITHUB_API_RELEASES)
    for release in releases:
        assets = release.get("assets", [])
        turnip_assets = [
            a for a in assets
            if a["name"].lower().endswith(".zip") and "turnip" in a["name"].lower()
        ]
        if turnip_assets:
            return release, turnip_assets
    return None, []


def sanitize_suffix(name):
    """Generate a clean Android package name suffix from driver name."""
    clean = re.sub(r"[^a-zA-Z0-9]", "", name).lower()
    if clean.startswith("turnip"):
        clean = clean[len("turnip"):]
    if not clean:
        clean = "driver"
    return f".turnip{clean}"


def package_driver(zip_path, zip_name, release_tag, output_dir):
    print(f"\nProcessing {zip_name}...")
    with tempfile.TemporaryDirectory() as extract_dir:
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(extract_dir)

        # Look for libvulkan_freedreno.so
        so_path = None
        for root, _, files in os.walk(extract_dir):
            for file in files:
                if file == "libvulkan_freedreno.so":
                    so_path = os.path.join(root, file)
                    break
            if so_path:
                break

        if not so_path:
            print(f"Warning: No libvulkan_freedreno.so found in {zip_name}. Skipping.")
            return None

        # Look for meta.json
        meta_name = ""
        meta_version = ""
        meta_path = None
        for root, _, files in os.walk(extract_dir):
            for file in files:
                if file == "meta.json":
                    meta_path = os.path.join(root, file)
                    break
            if meta_path:
                break

        if meta_path and os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta_data = json.load(f)
                    meta_name = meta_data.get("name", "")
                    meta_version = meta_data.get("driverVersion", "")
            except Exception as e:
                print(f"Notice: Failed to read meta.json: {e}")

        base_name = os.path.splitext(zip_name)[0]
        driver_name = meta_name if meta_name else base_name.replace("_", " ")
        app_suffix = sanitize_suffix(base_name)
        version_name = release_tag

        target_so_dir = os.path.join("app", "src", "main", "jniLibs", "arm64-v8a")
        os.makedirs(target_so_dir, exist_ok=True)
        target_so = os.path.join(target_so_dir, "libvulkan_freedreno.so")
        shutil.copy2(so_path, target_so)

        print(f"Driver Name: {driver_name}")
        print(f"App Suffix: {app_suffix}")
        print(f"Version Name: {version_name}")

        cmd = [
            "./gradlew",
            "clean",
            "assembleRelease",
            f"-PdriverName={driver_name}",
            f"-PappSuffix={app_suffix}",
            f"-PversionName={version_name}",
        ]
        res = subprocess.run(cmd)
        if res.returncode != 0:
            raise RuntimeError(f"Gradle build failed for {zip_name}")

        unsigned_apk = os.path.join("app", "build", "outputs", "apk", "release", "app-release-unsigned.apk")
        if not os.path.exists(unsigned_apk):
            raise RuntimeError(f"APK output not found: {unsigned_apk}")

        final_apk_name = f"{base_name}.apk"
        final_apk_path = os.path.join(output_dir, final_apk_name)
        shutil.copy2(unsigned_apk, final_apk_path)
        print(f"Successfully generated: {final_apk_path}")
        return final_apk_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["check", "get-matrix", "build-single", "build"], default="build",
                        help="check: check if new release exists; get-matrix: output matrix JSON; build-single: build a specific zip; build: build all")
    parser.add_argument("--last-tag", default="",
                        help="The last processed release tag")
    parser.add_argument("--zip-url", default="",
                        help="URL of the zip to build in build-single mode")
    parser.add_argument("--zip-name", default="",
                        help="Name of the zip to build in build-single mode")
    parser.add_argument("--output-dir", default="dist",
                        help="Output directory for packaged APKs")
    args = parser.parse_args()

    release, assets = find_latest_turnip_release()
    if not release:
        print("No Turnip release found in upstream repository.")
        sys.exit(1)

    tag_name = release["tag_name"]
    print(f"Latest Turnip Release: {tag_name} ({release.get('name', '')})")

    # If checking whether new
    if args.mode == "check":
        has_update = "true" if not args.last_tag or args.last_tag.strip() != tag_name.strip() else "false"
        print(f"Check result: has_update={has_update}, tag_name={tag_name}")
        matrix_data = [
            {
                "name": a["name"],
                "url": a["browser_download_url"],
                "base": a["name"][:-4] if a["name"].lower().endswith(".zip") else a["name"]
            }
            for a in assets
        ]
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write(f"has_update={has_update}\n")
                f.write(f"tag_name={tag_name}\n")
                f.write(f"matrix={json.dumps(matrix_data)}\n")
        return

    if args.mode == "get-matrix":
        matrix_data = [
            {
                "name": a["name"],
                "url": a["browser_download_url"],
                "base": a["name"][:-4] if a["name"].lower().endswith(".zip") else a["name"]
            }
            for a in assets
        ]
        print(f"Found {len(matrix_data)} Turnip assets.")
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write(f"tag_name={tag_name}\n")
                f.write(f"matrix={json.dumps(matrix_data)}\n")
        return

    if args.mode == "build-single":
        if not args.zip_url or not args.zip_name:
            print("Error: --zip-url and --zip-name are required for build-single mode.")
            sys.exit(1)
        os.makedirs(args.output_dir, exist_ok=True)
        with tempfile.TemporaryDirectory() as dl_dir:
            dest_zip = os.path.join(dl_dir, args.zip_name)
            print(f"\nDownloading {args.zip_name} from {args.zip_url}...")
            urllib.request.urlretrieve(args.zip_url, dest_zip)
            apk_path = package_driver(dest_zip, args.zip_name, tag_name, args.output_dir)
            apk_name = os.path.basename(apk_path) if apk_path else ""
            if "GITHUB_OUTPUT" in os.environ:
                with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                    f.write(f"apk_name={apk_name}\n")
                    f.write(f"apk_path={apk_path}\n")
        return

    os.makedirs(args.output_dir, exist_ok=True)
    with tempfile.TemporaryDirectory() as dl_dir:
        for asset in assets:
            zip_name = asset["name"]
            dl_url = asset["browser_download_url"]
            dest_zip = os.path.join(dl_dir, zip_name)
            print(f"\nDownloading {zip_name} from {dl_url}...")
            urllib.request.urlretrieve(dl_url, dest_zip)
            package_driver(dest_zip, zip_name, tag_name, args.output_dir)

    print(f"\nAll Turnip drivers for {tag_name} packaged into {args.output_dir}:")
    for f in os.listdir(args.output_dir):
        if f.endswith(".apk"):
            print(f" - {f}")

    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"tag_name={tag_name}\n")


if __name__ == "__main__":
    main()
