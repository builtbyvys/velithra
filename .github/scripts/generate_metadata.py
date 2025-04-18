#!/usr/bin/env python3

import os
import json
import hashlib
import datetime
import shutil


def calc_sha256(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def main():
    os.makedirs("./site", exist_ok=True)
    os.makedirs("./site/files", exist_ok=True)

    with open("./ota_source.json", "r") as f:
        source_info = json.load(f)

    build = source_info["build"]
    timestamp = datetime.datetime.now().isoformat()

    output_filename = f"custota-{build}.zip"
    output_path = f"./site/files/{output_filename}"
    shutil.copy("./custota.zip", output_path)

    sha256 = calc_sha256(output_path)

    # create or update metadata.json
    try:
        with open("./site/metadata.json", "r") as f:
            metadata = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        metadata = {"updates": []}

    update_info = {
        "build": build,
        "timestamp": timestamp,
        "filename": output_filename,
        "url": f"./files/{output_filename}",
        "size": os.path.getsize(output_path),
        "sha256": sha256,
        "source_url": source_info["url"],
        "source_sha256": source_info["sha256"],
        "changes": ["Updated to latest Google OTA", "Includes KernelSU (Next branch)"],
    }

    metadata["updates"] = [update_info] + metadata.get("updates", [])
    metadata["current_build"] = build
    metadata["last_updated"] = timestamp

    with open("./site/metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    gen_index(metadata)

    os.makedirs("./site/root", exist_ok=True)
    os.makedirs("./site/rootless", exist_ok=True)
    os.makedirs("./site/.well-known/custota", exist_ok=True)

    with open("./site/root/metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    with open("./site/rootless/metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    with open("./site/metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    with open("./site/.well-known/custota/cheetah.json", "w") as f:
        rootless_metadata = {
            "url": f"https://{os.environ.get('GITHUB_REPOSITORY_OWNER', 'builtbyvys')}.github.io/{os.environ.get('GITHUB_REPOSITORY', 'repo').split('/')[-1] or 'velithra'}/rootless/metadata.json"
        }
        json.dump(rootless_metadata, f, indent=2)

    print(f"Generated metadata and site content for build {build}")


def gen_index(metadata):
    html = (
        """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>custOTA Updates for Pixel 7 Pro</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        h1 {
            color: #333;
        }
        .update {
            border: 1px solid #ddd;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 5px;
        }
        .update h2 {
            margin-top: 0;
        }
        pre {
            background: #f4f4f4;
            padding: 10px;
            border-radius: 3px;
            overflow-x: auto;
        }
        .timestamp {
            color: #666;
            font-style: italic;
        }
    </style>
</head>
<body>
    <h1>custOTA Updates for Pixel 7 Pro (cheetah)</h1>
    <p>Last updated: """
        + metadata.get("last_updated", "")
        + """</p>
    
    <h2>Setup Instructions</h2>
    <h3>Root method</h3>
    <pre>adb shell "su -c 'setprop persist.custota.update_url https://builtbyvys.github.io/velithra/root/metadata.json'"</pre>
    
    <h3>Rootless method</h3>
    <p>Set this URL in your custOTA app:</p>
    <pre>https://builtbyvys.github.io/velithra</pre>
    
    <h2>Available Updates</h2>
"""
    )

    for update in metadata.get("updates", []):
        html += f"""
    <div class="update">
        <h3>Build {update.get('build', '')}</h3>
        <p class="timestamp">Released: {update.get('timestamp', '')}</p>
        <p><a href="{update.get('url', '')}">Download ({round(update.get('size', 0)/1024/1024, 2)} MB)</a></p>
        <p>SHA256: <code>{update.get('sha256', '')}</code></p>
        <h4>Changes:</h4>
        <ul>
"""
        for change in update.get("changes", []):
            html += f"            <li>{change}</li>\n"

        html += """        </ul>
    </div>
"""

    html += """
    <footer>
        <p>Generated by GitHub Actions</p>
    </footer>
</body>
</html>
"""

    with open("./site/index.html", "w") as f:
        f.write(html)


if __name__ == "__main__":
    main()
