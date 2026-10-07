# Release gates

This repository produces an **App Sandbox beta** for GitHub sharing. It is not a notarized or Marketplace-approved stable release.

## Current status (0.3.1.0)

The user confirmed entry works and return works after fully restarting Stream Deck. During updates, the host retained a stale return target and logged `Profile not found`; reopening the profile alone did not clear it. Close and reopen Stream Deck after updating, then test entry and return from the existing profile. This is a known upgrade limitation, not a proven permanent fix.

Both bundled profile display names are Mac Dock; their internal routing names remain Dock14 and Dock14Mobile. Each archive contains one profile. The installer alone is sufficient: drag DockDeck → Open Dock into an existing profile; the separate entry profile is optional.

Distribution preflight checks the actual installer after extraction, including signature integrity, Developer ID, timestamp, hardened runtime, exact entitlements, stapled ticket and Gatekeeper:

```sh
python3 scripts/release_check.py dist/local.dockdeck.streamDeckPlugin
```

Current result: signature integrity/runtime/permissions pass; publisher identity, Developer ID, timestamp and notarization remain blocked. A passing preflight does not replace clean-machine or hardware QA.

## Local verification

```sh
python3 scripts/package.py
sh scripts/test.sh
python3 tests/sandbox.py
python3 tests/integration.py
```

The latter tests require a normal macOS GUI user session and local TCP access. The sandbox probe uses only synthetic data and verifies denied file read/write outside its container plus denied inbound bind. The production binary's signed entitlements must exactly equal the tested policy.

For explicit Finder activation verification, compile `tests/frontmost.swift` into `.build/frontmost` then run `python3 tests/integration.py --launch-finder`. This brings Finder forward. It does not prove physical hardware events.

## Public release blockers

Model, packaging, sandbox and mock-host integration checks have passed locally. These checks do not establish clean-recipient or physical-device compatibility.

- [ ] Permanent publisher identity, bundle/plugin identifier and support process chosen.
- [x] MIT license included with generic project attribution.
- [ ] Developer ID Application certificate available.
- [ ] Apple notarization accepted and ticket stapled; Gatekeeper assessment passes after download onto a separate Mac.
- [ ] Physical MK.2 test: entry, launch of closed app, focus of running app, correct return, unplug/reconnect, sleep/wake, Stream Deck restart.
- [ ] Clean recipient Mac: plugin + shared entry profile import, app enumeration, no unexpected permission prompts.
- [ ] Supported macOS matrix actually exercised. Current local checks do not establish macOS 13 compatibility.
- [x] Official Stream Deck CLI validation of the current beta with updated schemas.
- [ ] Marketplace/product metadata review and repeat validation of the final signed artifact.
- [ ] Independent security review if marketed with stronger security assurances.

Mark GitHub downloads as pre-releases while these stable-release gates remain outstanding. Do not disable Gatekeeper, SIP, quarantine or TCC to make tests pass. Do not broaden entitlements silently.

## Signing and notarization

Use a Developer ID Application certificate installed by the developer. Keep secrets in Keychain; never store certificate passwords/API keys in this repository or paste them in chat.

```sh
python3 scripts/package.py --identity 'Developer ID Application: PUBLISHER (TEAMID)'
# After local tests pass, explicitly submit the signed app to Apple:
python3 scripts/notarize.py --keychain-profile YOUR_EXISTING_PROFILE
python3 tests/package.py
python3 scripts/share.py
python3 scripts/release_check.py dist/local.dockdeck.streamDeckPlugin
```

`notarize.py` refuses ad-hoc signatures, submits to Apple's service, requires Accepted, staples and validates the ticket, performs Gatekeeper assessment, then recreates the plugin archive. Do not run package.py after notarization because rebuilding invalidates the approved artifact. Submission has not been performed in this workspace.

The developer must replace provisional `local.dockdeck` / `local.dockdeck.runtime` identifiers consistently before public distribution, including profile/action IDs, test expectations and entitlements' identity context. Changing identifiers after users install is a migration, not a cosmetic rename.

## Support and limitations

Apple Silicon only; 15-key layout; first 14 apps; no AX/window snapshots/keyboard simulation. Temporary read-only exceptions allow `com.apple.dock` preferences and `~/Applications/`; default App Sandbox rules allow standard system/application resources. Apps installed in other private locations may be unavailable. Unpinned running apps use launch time rather than exact manually rearranged Dock order. Outbound network entitlement is broader than the fixed loopback endpoint used by the code.

Share packages are generated from clean metadata, not exported user profiles. No app list, device ID, local path, credentials or research repositories are bundled. A SHA-256 list detects mismatches only when obtained from a trusted channel; it is not publisher authentication.

## Public source and artifact hygiene

Export source with `python3 scripts/github_source.py`. The allowlist excludes existing Git history, build output, local logs, user profiles and unrelated projects. ZIP entries use fixed timestamps and normalized modes. Symbolic links are rejected. The source license uses generic project attribution.

Use a fresh Git repository and an explicit non-personal author and committer identity. Inspect commit metadata before pushing. Do not publish diagnostic snapshot output, local logs, signing credentials or account screenshots. An automated multi-model review found no personal paths, email addresses, credentials or device serials in the reviewed beta; this is not an independent security audit or a guarantee that vulnerabilities are absent.
