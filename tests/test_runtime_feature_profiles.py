"""Game-free contract checks for title-owned runtime feature registration.

python -I -B tests/test_runtime_feature_profiles.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    api = (ROOT / "gpu" / "vk" / "vk_api.h").read_text(encoding="utf-8")
    backend = (ROOT / "host" / "rx_backend.c").read_text(encoding="utf-8")
    runtime = (ROOT / "host" / "hos_main.c").read_text(encoding="utf-8")
    menu = (ROOT / "gpu" / "vk" / "vk_menu.cpp").read_text(encoding="utf-8")

    # The versioned executable/renderer boundary carries explicit, optional capabilities.
    assert "#define MKWVK_API_VERSION 15" in api
    assert "MKWVK_GAME_FEATURE_OOT_DEBUG = 1u << 0" in api
    assert "uint32_t (*game_features)(void);" in api
    assert "host_romfs_dir, host_wide_menus, host_game_features," in backend

    # Ocarina features require both the known program ID and the full supported build ID.
    assert "int hos_game_is_oot(void)" in runtime
    assert "hos_program_id == 0x0400486024DEC000ULL" in runtime
    assert '!strcmp(hos_main_build_id, "e0f3ccfaf50065ae4ea01eb5aeb13b1a45da3348")' in runtime
    assert "return hos_game_is_oot() ? MKWVK_GAME_FEATURE_OOT_DEBUG : 0;" in backend

    # The renderer must not infer title support from HOS_OOT_CHEATS or generic debug settings.
    assert "oot_debug_features = host && host->game_features &&" in menu
    assert "return oot_debug_features && (cheats_env || opts.debug_tools);" in menu
    assert "if (!oot_debug_features) return 0;" in menu
    assert "return oot_debug_features ? cheat_action.exchange" in menu

    # Host-side entry points remain inert if an Ocarina hook is reached for another image.
    for signature, guard in (
        ("int hos_oot_hearts_enabled(void)", "if (!hos_game_is_oot()) return 0;"),
        ("int hos_oot_is_player(Ctx *c, uint64_t actor)", "if (!hos_game_is_oot()) return 0;"),
        ("void hos_oot_cct_speed(Ctx *c, uint64_t controller, int per_second)", "if (!hos_game_is_oot()) return;"),
        ("static void oot_update_player_cheats(Ctx *c, uint64_t actor, uint64_t components)", "if (!hos_game_is_oot()) return;"),
        ("void hos_oot_free_view(Ctx *c, uint64_t view)", "if (!hos_game_is_oot()) return;"),
    ):
        start = runtime.index(signature)
        assert guard in runtime[start:start + 400], signature

    print("PASS: Ocarina runtime features are explicitly registered and exact-build gated")


if __name__ == "__main__":
    main()
