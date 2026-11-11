# Multi-game architecture: audit and proposed boundaries

Status: architecture plan with profile-driven lift patches and runtime feature registration implemented on `refactor/nx2-game-profiles`; full tests and game validation remain outstanding.

This document records the current title-specific seams found in Hookshot and proposes a staged way to separate them from the shared Switch 2 recompilation pipeline. It is not a claim that another title is supported.

## Goal and non-goals

The goal is to let Hookshot host multiple independently verified Switch 2 game targets while reusing the loader, AArch64 lifter, code generator, compiler pipeline, Horizon OS implementation, NVN2 implementation, and Vulkan replay wherever their contracts genuinely match.

A profile is identification and configuration, not compatibility. Registering a title must never make the builder accept it unless the required title-specific pipeline and runtime behavior are present and tested.

This work does not attempt to support Switch 1, emulate a console, bundle game data, or infer compatibility from a title ID alone.

## Current pipeline

1. nx2/dump.py characterizes a user's local dump: NPDM/program identity, module build IDs, Switch 2 platform signals, SDK/API signals, and optional RomFS shader/package names.
2. nx2/nup.py, nx2/unpack.py, nx2/nso2.py, and nx2/image.py extract/load modules, decompress NSOs, relocate the image, and bind imports.
3. nx2/lift.py, nx2/insn.py, nx2/lift_fixes.py, nx2/poll.py, and nx2/chunks.py translate guest AArch64 code into C.
4. nx2/standalone.py identifies HLE functions, generates stubs and image metadata, and routes SDK NVN2 exports.
5. nx2/build.py compiles lifted code and links the host runtime and Vulkan backend.
6. host/ implements Horizon-facing services and host/nvn_native.c implements native NVN2 behavior; gpu/vk/ translates shader programs and replays GPU work through Vulkan.

The shared core is already substantial. It should remain shared by default; game-specific behavior should be attached through explicit interfaces rather than copied wholesale into a per-title fork.

## Confirmed title-specific seams

### Build and executable identity

- nx2/game_profiles.py now holds the current Ocarina of Time build prefix (e0f3ccfa) and the profile lookup introduced on the working branch.
- nx2/make_game.py uses that lookup for its supported-build check.
- nx2/oot_patches.py still has a separate exact LIFE_BUILD_ID fingerprint used to gate a patch-sensitive lifting path.
- nx2/standalone.py emits hos_program_id and hos_main_build_id into generated hos_image.c.
- nx2/build.py still writes mkw_info.c with mkw_image_base and mkw_main_build_id. These names are inherited from the fork and should not be treated as a clean multi-title identity interface.
- host/hos_main.c has hos_game_is_mkw() checking an MKW build ID. This is an explicit inherited title hook and should be preserved only where MKW compatibility is intentional, not confused with Hookshot's title selection.

### Lift-time game modifications

- nx2/lift.py unconditionally installs oot_wide, oot_jitter, and oot_occlusion when making a standalone lift.
- The same file imports oot_patches and uses its exact build fingerprint to enable a particular chunks.edit_c behavior.
- nx2/oot_wide.py, nx2/oot_jitter.py, and nx2/oot_occlusion.py inject title-specific edits during lifting.
- nx2/oot_native_resolution.py and nx2/oot_patches.py edit generated C by matching known function heads, instruction-derived text, labels, and offsets. They are intentionally tied to known code shapes and must not be applied to another title merely because a profile exists.
- nx2/oot_patches.py also contains gameplay/UI feature hooks (movement, free view, mouse camera, menu focus/tick, text speed, frame timing, movie timing, and optional heart protection).

### Runtime and user-facing title features

- host/hos_main.c contains a large Ocarina-specific feature surface: heart protection, player checks, movement speed, inventory editing, game time, teleport destinations, and other game-state-aware operations.
- gpu/vk/oot_cheat_items.h and related menu code expose Ocarina-specific item names and actions.
- host/hos.h exposes generic generated identity (hos_program_id, hos_main_build_id) but also legacy MKW naming and hooks.
- host/nvn_native.c contains some explicit Ocarina assumptions, including depth-mode behavior. Other NVN2 device limits, shader conventions, and proc coverage are based on observed titles/SDK behavior and need evidence before being classified as universal.

### Build and shader behavior

- nx2/build.py has Ocarina-specific FFmpeg commentary (AV1 movie support), a camera-jitter dependency on nx2/oot_jitter.py, and inherited mkw_* naming in generated metadata and compile defines.
- gpu/vk/vk_shader.cpp contains Ocarina-specific shader optimization/workaround references alongside shared Ampere/NVN2 translation. Each workaround needs to be classified by whether it is a title bug, a shader/compiler rule, or a generally valid hardware rule.
- RomFS layout, shader package names, NVN proc usage, SDK version, device limits, service set, and startup behavior can vary by title/version. They should be recorded as observed compatibility requirements, not guessed profile defaults.

## Proposed architecture boundaries

### 1. Shared platform layer

Owns platform invariants and reusable mechanisms:

- Switch 2 dump/container and NSO parsing, relocation, image construction.
- AArch64 instruction translation and generic lift/code-generation machinery.
- Generic import discovery, HLE dispatch mechanisms, thread/memory primitives, and common Horizon service implementations.
- NVN2 object/proc machinery and Vulkan replay where behavior is confirmed to be API/platform-level.
- Host compiler and packaging infrastructure.

A feature belongs here only when its contract is supported by more than one title or by a documented platform/API specification. Avoid introducing title conditionals into shared low-level code where a strategy or capability interface is sufficient.

### 2. Game profile and version identity

A profile should describe immutable identity and validated compatibility facts, not contain arbitrary executable code. Candidate data, introduced only when required by real callers:

- Stable internal game key and display name.
- Program ID(s) and supported update/version identifiers.
- Exact module build fingerprints (at minimum main; optionally other modules when a feature depends on them).
- Platform/SDK/API facts observed during dump inspection.
- References to declared title-specific lift patch sets, runtime feature sets, and shader workarounds.
- A compatibility status/requirement declaration so "identified", "liftable", "buildable", and "playable" cannot be conflated.

The profile registry must reject ambiguous matches. Matching should use the strongest available identity (program ID plus version/build fingerprint), not a short build prefix by itself, once the full identity is available. Existing behavior must remain unchanged until validation is deliberately tightened with regression tests.

Do not put game dump bytes, derived code, keys, offsets discovered from private game data, or generated game artifacts in the repository.

### 3. Title-specific extension points

Keep title-specific work in separately named modules with explicit registration:

- Lift patches: an ordered set of patch functions with declared preconditions and required/optional status. A required patch mismatch should fail the build with a clear diagnostic; optional patches may report that they were not applied. The profile-selected dispatcher now lives in `nx2/lift_patches.py`: it lazily loads pre-discovery hook modules and the post-write C patch module only for a profile that names a registered patch set. Profiles with no patch set use only shared lifting.
- Runtime features: a title-owned registration for optional UI/cheat/game-state features. The first boundary is implemented: `host/rx_backend.c` exports the exact-build-selected Ocarina debug capability through `MkwVkHost.game_features`, and the renderer gates its Ocarina debug tools on that capability. Host Ocarina entry points also fail closed for any other image. Future title features should add explicit capability bits and title-owned implementations rather than exposing game-specific controls by default.
- Shader workarounds: separately named, narrowly scoped transformations with evidence and tests; do not mix them into generic shader lowering without proving they are universal.
- Data/layout adapters: title-specific save, RomFS, movie, input, and game-data behavior should be separate from common OS/API implementations.

A title extension must declare which executable/version fingerprints it applies to. It must not silently match another version or title.

### 4. Compatibility capability model

Avoid a single boolean "supported". Track independent stages:

- identified: dump identity is recognized;
- parsed: modules and required metadata load;
- liftable: instruction set and relocations are covered;
- buildable: generated code and runtime link;
- bootable: startup and required HLE imports work;
- renderable: the title produces correct frames with the selected backend;
- playable: required input, save, audio, video, and progression paths work.

The builder should only offer a production build for a profile whose declared minimum stage is actually met. Diagnostics should identify the first unmet stage and missing requirement.

## Suggested implementation sequence

1. Inventory and tests: record current coupling points; add game-free source/contract tests before moving code.
2. Identity cleanup: make generated identity consistently generic (hos_*), remove new dependencies on legacy mkw_* symbols, and preserve any still-required MKW hooks behind explicit identity checks.
3. Lift patch registry: **implemented on `refactor/nx2-game-profiles`** in `nx2/lift_patches.py`. Ocarina's pre-discovery hooks and post-write C edits are selected by its profile; unknown/shared-only profiles do not import those modules. The existing exact-build gate for strict Ocarina patches is preserved. Full test-suite and game-build verification remain outstanding.
4. Runtime feature registration: **initial boundary implemented**. The versioned Vulkan host API now carries title feature bits; the Ocarina debug menu is enabled only for the exact supported program/build identity, and host Ocarina hooks fail closed for other images. The Ocarina implementation remains in `host/hos_main.c` for now; moving its implementation into a dedicated translation unit is a separate follow-up once its shared dependencies are isolated.
5. Shader workaround classification: tag each current workaround with scope, evidence, and a game-free regression test; keep unknown cases title-scoped.
6. Second-title feasibility spike: choose a legally obtained local dump, inspect it locally, and produce a compatibility matrix. Do not register it as supported until the pipeline has passed the appropriate stage tests and an in-game validation run.
7. End-to-end verification: run python -I -B tests/run_all.py, build/test without game data in CI, and perform local game testing. Report unavailable OS/GPU/title tests honestly.

Each implementation step should be a separate reviewable change. Do not attempt a large "genericize everything" refactor.

## Open design questions

- Should the canonical identity be a single GameProfile plus separate GameVersion entries, or should each supported executable/update be a complete immutable profile? Prefer the latter if patches and runtime behavior differ by update.
- Which parts of host/nvn_native.c are true NVN2 semantics, and which are workarounds for the observed Ocarina/MKW titles?
- Which shader workarounds in gpu/vk/ are Ocarina-only, MKW-only, or general Ampere/NVN2 lowering requirements?
- What is the minimal stable interface for a title's patch set and runtime feature registration without making the build pipeline plugin-heavy?
- Which metadata can be verified from a dump without needing to read or publish any proprietary game data?

## Safety and testing constraints

- No game files, keys, decrypted modules, lifted C, generated assets, or other artifacts derived from a game dump may be committed or uploaded.
- CI and game-free tests must not require a dump.
- Source-reading tests are part of the contract; update them alongside refactors rather than weakening them.
- Keep Windows and Linux behavior working.
- Do not claim another title is supported based only on a profile entry or a successful compile.
