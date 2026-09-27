"""Export a verified linux/amd64, code-and-data Docker delivery bundle."""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = "PestKG_A_Data_Release_v1.0"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tracked_data(root):
    paths = subprocess.check_output(
        ["git", "ls-files", "-z", "--", f"data/releases/{RELEASE}", "data/reference-graphs"],
        cwd=root,
    ).decode("utf-8").split("\0")
    files = [Path(path) for path in paths if path]
    parquet_count = 0
    for relative in files:
        source = root / relative
        if not source.is_file() or not source.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Missing or unsafe tracked data: {relative}")
        if source.suffix == ".parquet":
            parquet_count += 1
            with source.open("rb") as stream:
                if stream.read(4) != b"PAR1":
                    raise ValueError(f"Not materialized Parquet (check Git LFS): {relative}")
    if parquet_count < 9:
        raise ValueError("Expected seven primary and two reference Parquet tables")
    return files


def build(tag, namespace, caddy, output):
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}", tag):
        raise ValueError("Invalid Docker image tag")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    images = [f"{namespace}/api:{tag}", f"{namespace}/web:{tag}", caddy]
    metadata = json.loads(subprocess.check_output(["docker", "image", "inspect", *images], text=True))
    for index, item in enumerate(metadata):
        if (item["Os"], item["Architecture"]) != ("linux", "amd64"):
            raise ValueError(f"Wrong image platform: {images[index]}")
        labels = item["Config"].get("Labels") or {}
        if index < 2 and (labels.get("org.opencontainers.image.revision") != commit
                          or labels.get("org.opencontainers.image.version") != tag):
            raise ValueError(f"Image does not match this commit and tag: {images[index]}")
    data = tracked_data(ROOT)
    name = f"pestkg-server-{tag}-linux-amd64"
    output.mkdir(parents=True, exist_ok=True)
    stage = output / name
    stage.mkdir()  # Never overwrite an earlier delivery.
    for source, destination in [
        ("infra/docker-compose.offline.yml", "docker-compose.yml"),
        ("infra/caddy/Caddyfile", "Caddyfile"),
        ("docs/operations/DEPLOYMENT_DOCKER_ZH.md", "DEPLOYMENT.md"),
    ]:
        shutil.copy2(ROOT / source, stage / destination)
    env = (ROOT / "infra/offline.env.example").read_text(encoding="utf-8")
    env = env.replace("REPLACED_BY_BUNDLE_BUILDER", tag)
    env = env.replace("PESTKG_IMAGE_NAMESPACE=pestkg", f"PESTKG_IMAGE_NAMESPACE={namespace}")
    env = env.replace("CADDY_IMAGE=caddy:2.11.4-alpine", f"CADDY_IMAGE={caddy}")
    (stage / ".env.example").write_text(env, encoding="utf-8")
    for relative in data:
        destination = stage / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
    subprocess.run(["docker", "image", "save", "-o", str(stage / "images.tar"), *images], check=True)
    manifest = {
        "bundle": name, "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": commit, "platform": "linux/amd64", "base_release_id": RELEASE,
        "images": [{"name": name, "id": item["Id"], "repo_digests": item.get("RepoDigests", [])}
                   for name, item in zip(images, metadata)],
        "data_files": len(data),
    }
    (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    sums = [f"{sha256(path)}  {path.relative_to(stage).as_posix()}\n"
            for path in sorted(stage.rglob("*")) if path.is_file()]
    (stage / "SHA256SUMS").write_text("".join(sums), encoding="utf-8")
    archive = output / f"{name}.tar.gz"
    with tarfile.open(archive, "w:gz", compresslevel=1) as stream:
        stream.add(stage, arcname=name)
    (output / f"{archive.name}.sha256").write_text(f"{sha256(archive)}  {archive.name}\n", encoding="utf-8")
    print(archive.resolve(), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--namespace", default="pestkg")
    parser.add_argument("--caddy", default="caddy:2.11.4-alpine")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/deploy")
    args = parser.parse_args()
    build(args.tag, args.namespace, args.caddy, args.output.resolve())
