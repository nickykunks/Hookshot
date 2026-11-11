"""Game-free checks for profile-selected title-specific lift patches.

python -I -B tests/test_lift_patches.py
"""
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "nx2"))

from game_profiles import GameProfile, OOT_REMAKE
import lift_patches


class LiftPatchRegistryTests(unittest.TestCase):
    def test_oot_profile_selects_its_patch_set(self):
        patch_set = lift_patches.patch_set_for_profile(OOT_REMAKE)
        self.assertIsNotNone(patch_set)
        self.assertEqual(
            patch_set.pre_discovery_modules,
            ("oot_wide", "oot_jitter", "oot_occlusion"),
        )
        self.assertEqual(patch_set.post_write_module, "oot_patches")
        self.assertEqual(
            patch_set.required_build_id,
            "e0f3ccfaf50065ae4ea01eb5aeb13b1a45da3348",
        )

    def test_unknown_or_shared_only_profiles_have_no_title_patches(self):
        shared = GameProfile("future-game", "Future Game", "12345678")
        unknown = GameProfile("future-game", "Future Game", "12345678", "not-registered")
        self.assertIsNone(lift_patches.patch_set_for_profile(None))
        self.assertIsNone(lift_patches.patch_set_for_profile(shared))
        self.assertIsNone(lift_patches.patch_set_for_profile(unknown))

    def test_pre_discovery_hooks_only_install_for_standalone_oot(self):
        import oot_wide
        import oot_jitter
        import oot_occlusion
        lifter, image = object(), object()
        with mock.patch.object(oot_wide, "install") as wide, \
             mock.patch.object(oot_jitter, "install") as jitter, \
             mock.patch.object(oot_occlusion, "install") as occlusion:
            self.assertEqual(
                lift_patches.install_pre_discovery(lifter, image, OOT_REMAKE, standalone=True),
                3,
            )
            wide.assert_called_once_with(lifter, image)
            jitter.assert_called_once_with(lifter, image)
            occlusion.assert_called_once_with(lifter, image)
            self.assertEqual(
                lift_patches.install_pre_discovery(lifter, image, OOT_REMAKE, standalone=False),
                0,
            )

    def test_unrecognized_profile_does_not_import_or_install_oot_hooks(self):
        shared = GameProfile("future-game", "Future Game", "12345678")
        with mock.patch.object(lift_patches.importlib, "import_module") as importer:
            self.assertEqual(
                lift_patches.install_pre_discovery(object(), object(), shared, standalone=True),
                0,
            )
            self.assertFalse(
                lift_patches.apply_post_write("unused", shared, standalone=True, main_build_id="12345678")
            )
            importer.assert_not_called()

    def test_lift_and_chunk_writer_route_through_the_registry(self):
        lift = (ROOT / "nx2" / "lift.py").read_text(encoding="utf-8")
        chunks = (ROOT / "nx2" / "chunks.py").read_text(encoding="utf-8")
        self.assertIn("profile_for_build_id(main_build)", lift)
        self.assertIn("install_pre_discovery(L, img, profile", lift)
        self.assertIn("chunks.edit_c(gen, L.stats, profile", lift)
        self.assertIn("apply_post_write(gen, profile", chunks)
        self.assertNotIn("oot_wide.install(L, img)", lift)
        self.assertNotIn("import oot_patches", lift)

    def test_post_write_keeps_exact_build_gate_for_strict_oot_patches(self):
        import oot_patches
        exact = "e0f3ccfaf50065ae4ea01eb5aeb13b1a45da3348"
        with mock.patch.object(oot_patches, "apply") as apply:
            self.assertTrue(lift_patches.apply_post_write(
                "gen", OOT_REMAKE, standalone=True, main_build_id=exact, whole=True
            ))
            apply.assert_called_once_with("gen", protect_hearts=True, required=True)
            apply.reset_mock()
            self.assertTrue(lift_patches.apply_post_write(
                "gen", OOT_REMAKE, standalone=True, main_build_id="e0f3ccfa" + "00" * 12, whole=True
            ))
            apply.assert_called_once_with("gen", protect_hearts=False, required=False)
            apply.reset_mock()
            lift_patches.apply_post_write(
                "gen", OOT_REMAKE, standalone=True, main_build_id=exact, whole=False
            )
            apply.assert_called_once_with("gen", protect_hearts=True, required=False)


if __name__ == "__main__":
    unittest.main()
