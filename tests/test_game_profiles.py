"""Game-free checks for title/build profile selection.

python -I -B tests/test_game_profiles.py
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "nx2"))

from game_profiles import GAME_PROFILES, OOT_REMAKE, profile_for_build_id


def main():
    assert GAME_PROFILES == (OOT_REMAKE,)
    assert OOT_REMAKE.game_id == "oot-remake"
    assert OOT_REMAKE.name == "The Legend of Zelda: Ocarina of Time remake"
    assert OOT_REMAKE.build_id_prefix == "e0f3ccfa"
    assert OOT_REMAKE.lift_patch_set == "oot-remake-1.1.1"

    # NSO module IDs contain a longer fingerprint; matching intentionally uses the
    # existing eight-character build prefix, preserving the old acceptance rule.
    assert OOT_REMAKE.matches_build_id("e0f3ccfa" + "12" * 12)
    assert profile_for_build_id("e0f3ccfa" + "12" * 12) is OOT_REMAKE
    assert profile_for_build_id("00000000" + "12" * 12) is None
    assert profile_for_build_id(None) is None

    source = (ROOT / "nx2" / "make_game.py").read_text(encoding="utf-8")
    assert "BUILD_ID" not in source, "make_game.py still owns a hard-coded build ID"
    assert "profile_for_build_id(bid)" in source, "the build check bypasses game profiles"
    assert "GAME_PROFILES" in source, "the unsupported-build message has no profile registry"

    print("PASS: build IDs resolve through the game profile registry")


if __name__ == "__main__":
    main()
