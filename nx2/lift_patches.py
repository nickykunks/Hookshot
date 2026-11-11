"""Dispatch title-specific lift patches through the selected game profile.

A game profile without a registered patch set receives only the shared lift.
Patch modules are imported lazily so unrelated titles do not load Ocarina code.
"""
from dataclasses import dataclass
import importlib


@dataclass(frozen=True)
class LiftPatchSet:
    """Title-specific hooks before discovery and C edits after code generation."""

    pre_discovery_modules: tuple[str, ...] = ()
    post_write_module: str | None = None
    required_build_id: str | None = None


PATCH_SETS = {
    "oot-remake-1.1.1": LiftPatchSet(
        pre_discovery_modules=("oot_wide", "oot_jitter", "oot_occlusion"),
        post_write_module="oot_patches",
        required_build_id="e0f3ccfaf50065ae4ea01eb5aeb13b1a45da3348",
    ),
}


def patch_set_for_profile(profile):
    """Return the registered patch set for a profile, or None for shared-only lifting."""
    if profile is None:
        return None
    return PATCH_SETS.get(getattr(profile, "lift_patch_set", None))


def install_pre_discovery(lifter, img, profile, *, standalone):
    """Install registered instruction-adjacent hooks before function discovery."""
    patch_set = patch_set_for_profile(profile)
    if not standalone or patch_set is None:
        return 0
    installed = 0
    for module_name in patch_set.pre_discovery_modules:
        module = importlib.import_module(module_name)
        module.install(lifter, img)
        installed += 1
    return installed


def apply_post_write(gen, profile, *, standalone, main_build_id, whole=True):
    """Apply the selected title's generated-C edits; no profile means no title-specific edits."""
    patch_set = patch_set_for_profile(profile)
    if patch_set is None or patch_set.post_write_module is None:
        return False
    module = importlib.import_module(patch_set.post_write_module)
    supported = standalone and main_build_id == patch_set.required_build_id
    module.apply(gen, protect_hearts=supported, required=supported and whole)
    return True
