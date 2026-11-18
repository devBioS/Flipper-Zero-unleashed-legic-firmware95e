# Unleashed 095e + LEGIC Prime

This branch ports the tested LEGIC Prime integration onto the exact Unleashed 095
source release, with the original Base and Extra Apps included in update packages.
The repository's original `dev` history is left intact.

## Source provenance

- Unleashed base: `unlshd-095`, `9c6327764c18fc8376b5941aa8bde79fe681fe8f`.
- LEGIC source: [official firmware PR #4468](https://github.com/flipperdevices/flipperzero-firmware/pull/4468).
- Actual PR base: `66613d2b46e4aa533aeaf8181d2a1e6566616a4e`.
- Imported PR head: `9ef097609fbebd540e5286dfbbe751b4daad4422`.
- App packs: `11nov2026`, with SHA-256 locks in `scripts/legic_prime/packs.lock.json`.

The port preserves Unleashed's EMV/Texkom support, numeric protocol IDs and NFC
plugin architecture. SDK API 88.27 adds LEGIC exports while retaining all original
88.26 exports. Release-only LTO for NFC, Sub-GHz, IR, Toolbox and Bit helpers keeps
the complete feature set below the radio/FUS boundary. Flash headroom is small;
check the per-build flash report rather than the raw `.free_flash` section.

LEGIC reading and emulation are available in the NFC application. Writing uses
the NFC CLI's `nfc legic wrbl` command, as in the source PR. User-reported tests
cover MIM256/MIM1024 reading, binary-equivalent Proxmark dumps and successful
emulation at real readers. Physical-tag writing, MIM22 and the full regression
matrix have not been confirmed.

## GitHub Actions and releases

The **Build and release Unleashed 095e LEGIC** workflow:

1. Checks out pinned submodules and the full source history.
2. Verifies existing NFC/API registrations and runs the host PRNG/CRC vectors.
3. Downloads checksum-locked Base and Extra Apps and verifies their FAP imports.
4. Builds `./fbt COMPACT=1 DEBUG=0 updater_package` with the existing FBT toolchain.
5. Checks the update archive, all 393 app-pack files, NFC plugins and flash limits.
6. Uploads the complete update package, SDK, SHA-256 checksums and build provenance.
7. Publishes a prerelease for pushes to `legic-prime-095e` and manual runs.
   A pushed tag matching `unlshd-095e-legic-*` publishes a regular release instead.
   Pull requests build artifacts only and have no release-write permissions.

GitHub-hosted Ubuntu runners supply Python, a host C compiler and GitHub CLI;
FBT bootstraps its pinned ARM toolchain. No personal access token is required by
the workflow: the publish job uses the repository-scoped `GITHUB_TOKEN` with
`contents: write`. Fork repositories may need Actions enabled in repository settings.

Automatic prerelease tags include the full source commit's first 12 hexadecimal
characters. Published releases are never silently overwritten: use a new commit
or a new release tag for changed files. Workflow runs serialize per branch/tag.

If this branch is not the default branch, its push trigger still runs. Set it as
the default branch if you want its manual **Run workflow** button available from
the default Actions view. The workflow does not change the default branch itself.

## Local build

From the repository root:

```sh
python3 scripts/legic_prime/build_release.py
```

Use an empty `release-artifacts` directory. The script downloads the original
095 Base and Extra packs, builds the firmware and SDK, and validates the result.
Generated app binaries, toolchains, build directories and release output are not
committed. No separate or unverified Extra Apps build flag is used.

For the standard manual build:

```sh
python3 scripts/legic_prime/prepare_packs.py
DIST_SUFFIX=unlshd-095e-legic ./fbt COMPACT=1 DEBUG=0 updater_package
```

## Installation and recovery

Download the release asset `flipper-z-f7-update-unlshd-095e-legic.tgz`, verify
`SHA256SUMS`, and install it through **Install from file** in qFlipper or the
Unleashed web updater. The SDK ZIP is not an installation package.

Before updating, back up the complete SD card including hidden `.int`, `apps_data`,
personal card files and custom apps. Keep an original Unleashed 095e update package
and a verified backup for rollback. To revert a booting device, install that original
package and restore the matching app/data backup as needed. For a non-booting device,
follow the [official firmware recovery instructions](https://docs.flipper.net/zero/basics/firmware-update/firmware-recovery).

The workflow never installs firmware on hardware. It does not publish the private
German integration, backup or hardware-test reports from the development workspace.
