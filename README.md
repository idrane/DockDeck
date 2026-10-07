# DockDeck

A macOS Dock for a 15-key Stream Deck. Show up to 14 apps and a Return key, launch or focus apps, and see running and foreground indicators.

**Current version: 0.3.1.0 beta.** The downloadable build is ad-hoc signed, not Developer ID signed or Apple-notarized. GitHub hosting does not change Gatekeeper requirements. Other Macs may block it; do not disable security protections to install it.

## Requirements

- Apple Silicon Mac. Intel binaries are not included.
- Compiled for macOS 13 or later; the full OS compatibility matrix has not been tested.
- Stream Deck 7.5 or later.
- A 5-column × 3-row layout on Stream Deck or Stream Deck Mobile.

## Install

**Only one file is needed:** [Download local.dockdeck.streamDeckPlugin](https://github.com/idrane/DockDeck/releases/download/v0.3.1.0-beta/local.dockdeck.streamDeckPlugin).

1. Download the plugin using the link above.
2. Double-click it to install with Stream Deck.
3. Select your device and usual profile.
4. Drag **DockDeck > Open Dock** onto an empty key.
5. Press that key on the hardware or tap it on Mobile. Accept the bundled profile installation if prompted.
6. Press an app key to launch or focus it. Press **Return** to return to the previous profile.

The plugin includes both Dock layouts. No separate profile, ZIP or source download is needed. To share DockDeck, send this single `.streamDeckPlugin` file. GitHub's automatic source archives are for developers only.

Clicking a key in the desktop editor selects it for editing. Enter the Dock using the physical/Mobile key, not the profile dropdown, so Stream Deck records the return destination.

## Auto-return

Select the **Open Dock** key in the editor. Set **Auto-return delay (seconds)** and use **Save** if needed. Settings belong to that key.

- `0`, an empty field, or **Disable** turns auto-return off (the default).
- Positive values up to 86400 seconds are accepted, including fractions.
- The Return key displays the remaining seconds, rounded up, with a small return arrow.
- The countdown begins when the Dock appears. Pressing an app does not reset it.
- Press Return at any time to return immediately. Leaving the Dock cancels the countdown.

## Limitations and troubleshooting

Finder and pinned apps come first, followed by unpinned running/recent apps, up to 14 total. Transient apps use launch order; manually rearranged transient Dock order is not reproduced exactly. Folders, Trash, minimized windows, badges and drag-and-drop are not supported.

If Return stops working after updating, fully quit and reopen Stream Deck, then enter through Open Dock. This cleared a stale host return target during testing; automatic recovery is not implemented.

Countdown behavior has protocol-level tests. Fresh-Mac installation, setting persistence and timing on all supported hardware still require release QA. Apps in private nonstandard locations may be inaccessible to the sandbox.

## Security

The native runtime uses macOS App Sandbox and hardened runtime. It reads Dock preferences and `~/Applications`, uses standard sandbox resources and its private container, and connects to Stream Deck at `127.0.0.1`. The network client entitlement itself permits outbound connections beyond loopback; the code limits its destination.

No Accessibility, Screen Recording, Full Disk Access or administrator permission is requested. No telemetry, shell/AppleScript execution or remote updater is included. See [SECURITY.md](SECURITY.md) for the precise scope and [RESEARCH.md](RESEARCH.md) for reviewed projects. No third-party runtime code is bundled.

## Build and test

Requires Apple command-line developer tools and Python 3. No third-party runtime packages are needed.

```sh
python3 scripts/package.py
sh scripts/test.sh
python3 tests/sandbox.py
python3 tests/integration.py
python3 scripts/share.py
```

Sandbox and integration tests require a normal macOS GUI session with local TCP access. They use synthetic test data. The optional `--launch-finder` integration mode activates Finder; see [RELEASE.md](RELEASE.md).

Generated files are in `dist/`. Build output, research checkouts, credentials and personal profiles do not belong in Git. Use `python3 scripts/github_source.py` to produce an allowlisted source archive for a clean repository.

## Distribution

GitHub can host the source and an explicitly marked beta Release before notarization. Developer ID signing and Apple notarization remain necessary for the intended verified-download experience. See [RELEASE.md](RELEASE.md) for signing, notarization and outstanding QA.

Licensed under the [MIT License](LICENSE). Copyright is attributed to DockDeck contributors.

## Uninstall

Remove DockDeck in Stream Deck's plugin manager, then remove unwanted Mac Dock/entry profiles and Open Dock keys. No separate login item or daemon is installed. The macOS sandbox container may remain after uninstalling.
