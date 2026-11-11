"""Game-free checks that generated recompilation identity is title-neutral.

python -I -B tests/test_recomp_identity.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    build = (ROOT / "nx2" / "build.py").read_text(encoding="utf-8")
    shim = (ROOT / "nx2" / "rt" / "eden_shim.c").read_text(encoding="utf-8")
    host = (ROOT / "nx2" / "rt" / "mkw_host.h").read_text(encoding="utf-8")

    # Generic image identity; the historical Mkw* DLL host ABI stays compatible.
    assert 'def write_recomp_info(out):' in build
    assert '"recomp_info.c"' in build
    assert "recomp_image_base" in build
    assert "recomp_main_build_id" in build
    assert "write_recomp_info(out)" in build
    assert "extern const uint64_t recomp_image_base;" in shim
    assert "extern const char recomp_main_build_id[];" in shim
    assert "info->image_base = recomp_image_base;" in shim
    assert "info->main_build_id = recomp_main_build_id;" in shim
    assert "mkw_image_base" not in build + shim
    assert "mkw_main_build_id" not in build + shim

    # This change must not rename the established DLL ABI.
    assert "MkwGameInfo" in host
    assert "mkw_recomp_attach" in host
    assert "mkw_recomp_lookup" in host

    print("PASS: generated identity is title-neutral; legacy DLL ABI is preserved")


if __name__ == "__main__":
    main()
