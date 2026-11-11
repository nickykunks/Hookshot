"""Per-title metadata used to identify game builds supported by the recompilation pipeline.

A profile is a declaration of a build the current pipeline has been prepared for. Adding a
profile does not by itself make another title compatible: its lifting, patches, Horizon/NVN2
behavior, assets, and runtime assumptions must also be implemented and tested.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class GameProfile:
    """The identity and main-module build fingerprint for one supported game version."""

    game_id: str
    name: str
    build_id_prefix: str
    lift_patch_set: str | None = None

    def matches_build_id(self, build_id):
        """Whether an NSO module ID belongs to this profile's supported build."""
        return isinstance(build_id, str) and build_id.startswith(self.build_id_prefix)


# The original Hookshot target. Keep its existing build fingerprint unchanged until the
# title-specific pipeline data and patches have been verified against another release.
OOT_REMAKE = GameProfile(
    game_id="oot-remake",
    name="The Legend of Zelda: Ocarina of Time remake",
    build_id_prefix="e0f3ccfa",
    lift_patch_set="oot-remake-1.1.1",
)

# Extend this registry only when the pipeline can actually build and run that title.
GAME_PROFILES = (OOT_REMAKE,)


def profile_for_build_id(build_id):
    """Return the supported game profile for an NSO build ID, or None when unknown."""
    return next((profile for profile in GAME_PROFILES if profile.matches_build_id(build_id)), None)
