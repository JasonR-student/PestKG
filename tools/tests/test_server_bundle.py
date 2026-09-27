import hashlib
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import build_server_bundle as bundle


class ServerBundleTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.files = [Path(f"data/releases/{bundle.RELEASE}/{index}.parquet") for index in range(9)]
        for relative in self.files:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"PAR1fixturePAR1")
        self.git_output = "\0".join(path.as_posix() for path in self.files).encode() + b"\0"

    def test_tracked_data_excludes_untracked_files(self):
        (self.root / "data/private-cache.parquet").write_bytes(b"PAR1")
        with patch.object(bundle.subprocess, "check_output", return_value=self.git_output):
            self.assertEqual(bundle.tracked_data(self.root), self.files)

    def test_lfs_pointer_or_missing_table_is_rejected(self):
        (self.root / self.files[0]).write_bytes(b"version https://git-lfs.github.com/spec/v1")
        with patch.object(bundle.subprocess, "check_output", return_value=self.git_output):
            with self.assertRaisesRegex(ValueError, "Not materialized Parquet"):
                bundle.tracked_data(self.root)
        (self.root / self.files[0]).unlink()
        with patch.object(bundle.subprocess, "check_output", return_value=self.git_output):
            with self.assertRaisesRegex(ValueError, "Missing or unsafe"):
                bundle.tracked_data(self.root)

    def test_bundle_has_checksums_manifest_and_matching_image_identity(self):
        for source in ["infra/docker-compose.offline.yml", "infra/caddy/Caddyfile",
                       "docs/operations/DEPLOYMENT_DOCKER_ZH.md", "infra/offline.env.example"]:
            path = self.root / source
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("PESTKG_IMAGE_TAG=REPLACED_BY_BUNDLE_BUILDER\n", encoding="utf-8")
        images = [{"Os": "linux", "Architecture": "amd64", "Id": f"sha256:{index}",
                   "Config": {"Labels": {"org.opencontainers.image.revision": "commit",
                                         "org.opencontainers.image.version": "test"}}}
                  for index in range(3)]

        def command(args, **kwargs):
            if args[0] == "docker":
                return json.dumps(images)
            return "commit\n" if args[1] == "rev-parse" else self.git_output

        def save(args, **kwargs):
            Path(args[4]).write_bytes(b"fixture image archive")

        with patch.object(bundle, "ROOT", self.root), \
                patch.object(bundle.subprocess, "check_output", side_effect=command), \
                patch.object(bundle.subprocess, "run", side_effect=save):
            bundle.build("test", "pestkg", "caddy:test", self.root / "output")
        stage = self.root / "output/pestkg-server-test-linux-amd64"
        self.assertEqual(json.loads((stage / "manifest.json").read_text())["git_commit"], "commit")
        self.assertIn("PESTKG_IMAGE_TAG=test", (stage / ".env.example").read_text())
        for line in (stage / "SHA256SUMS").read_text().splitlines():
            digest, relative = line.split("  ", 1)
            self.assertEqual(digest, hashlib.sha256((stage / relative).read_bytes()).hexdigest())
        with tarfile.open(stage.with_suffix(".tar.gz")) as archive:
            self.assertIn(stage.name + "/images.tar", archive.getnames())


if __name__ == "__main__":
    unittest.main()
