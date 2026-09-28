"""Focused Linux setup boundary checks; does not alter the backend test inventory."""

import io
import json
import runpy
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory

MODULE = runpy.run_path(str(Path(__file__).with_name("linux_setup.py")))


def rejects(operation, expected):
    try:
        operation()
    except RuntimeError as error:
        assert expected in str(error), str(error)
    else:
        raise AssertionError("Expected fail-closed rejection")


def main():
    with TemporaryDirectory(prefix="tosstoss-linux-contract-check-") as temporary:
        root = Path(temporary)
        target = root / "real"
        target.mkdir()
        link = root / "link"
        link.symlink_to(target, target_is_directory=True)
        rejects(lambda: MODULE["safe_path"](link / "child"), "symlink")
        fake = root / "node.exe"
        fake.write_bytes(b"MZfake Windows runtime")
        rejects(lambda: MODULE["native_elf"](fake), "ELF")
        (root / ".python-version").write_text(MODULE["PYTHON"])
        (root / ".node-version").write_text(MODULE["NODE"])
        (root / "package.json").write_text(json.dumps({"packageManager": "npm@" + MODULE["NPM"]}))
        for name in ["requirements.lock", "package-lock.json"]:
            (root / name).write_text("preserved lock")
        windows = root / ".venv/Scripts"
        windows.mkdir(parents=True)
        witness = windows / "python.exe"
        witness.write_bytes(b"preserve unexpected Windows environment")
        rejects(lambda: MODULE["setup"](root), "Unexpected existing environment")
        assert witness.read_bytes() == b"preserve unexpected Windows environment"
        assert not (root / "var").exists()
        archive = root / "runtime.tar"
        with tarfile.open(archive, "w") as tar:
            info = tarfile.TarInfo("runtime/bin/tool")
            info.size = 5
            tar.addfile(info, io.BytesIO(b"valid"))
        runtime = MODULE["unpack"](archive, root, "runtime")
        assert (runtime / "bin/tool").read_bytes() == b"valid"
        (runtime / "bin/tool").write_bytes(b"other")
        rejects(lambda: MODULE["unpack"](archive, root, "runtime"), "verified archive")
        rejects(lambda: MODULE["download"]("https://unused.invalid", fake, "0" * 64), "checksum")
    print(
        "Linux setup boundary checks: PASS (symlink, Windows ELF, environment preservation, "
        "verified extraction, altered runtime and bad checksum)"
    )


if __name__ == "__main__":
    main()
