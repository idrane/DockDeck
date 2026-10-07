# DockDeck — security scope

The runtime is an App Sandbox `.app` bundle, with hardened runtime signing. Local artifacts use ad-hoc signing. They are **sandbox beta builds, not notarized public releases**. There is no claim of zero vulnerabilities.

## Exact entitlements

`config/DockDeck.entitlements` is the source of truth. Tests require the production signature to match it exactly:

| Entitlement | Purpose | Limit |
| --- | --- | --- |
| `com.apple.security.app-sandbox` | OS-enforced sandbox | Container and standard macOS sandbox allowances remain available |
| `com.apple.security.network.client` | Stream Deck's local WebSocket | This OS permission also allows outbound remote connections; source code restricts the destination to literal `127.0.0.1` |
| `com.apple.security.temporary-exception.shared-preference.read-only` = `com.apple.dock` | Pinned/recent app settings | Read-only exception for one preference domain |
| `com.apple.security.temporary-exception.files.home-relative-path.read-only` = `/Applications/` | Apps installed in `~/Applications` | Read-only access to that entire folder, not the whole home directory |

No inbound-network/server, Apple Events, accessibility, camera, microphone, user-selected-files, downloads/documents, executable-memory, debugger or disable-library-validation entitlements are requested. No full-disk/admin access is requested. Standard application/system locations are readable under macOS's base sandbox policy; this is not an allowlist of only four files.

## Data and actions

The plugin reads Dock app URLs, app metadata/icons, running apps and the frontmost app. Key presses invoke `NSWorkspace.openApplication` or Stream Deck profile commands. It does not collect window contents, screenshots, keystrokes, clipboard data, credentials or documents. No telemetry, external server endpoints, runtime downloads, startup service, shell, AppleScript or child-process launching code is included. The asset writer is a build tool and is not shipped. The explicit `--snapshot` diagnostic prints app names and identifiers locally; ordinary runtime operation does not save app histories. Failed activation logs only an OS error code to Stream Deck.

## Defensive behavior

- Fixed loopback host and validated numeric port; ephemeral URLSession, proxy/cookie/cache disabled.
- Input capped at 64 KiB; unknown/malformed events ignored; action contexts, outbound queue and icon cache bounded.
- Only visible context/action/device matches can activate. Key bounds are validated and multi-actions are rejected. Open Dock accepts a bounded auto-return delay; settings cannot provide launch targets or shell commands.
- Launch targets come from the displayed Dock model; local `.app` bundles, bundle types, executable existence and volume locality are revalidated.
- Non-file/remote-host URLs, URL queries/fragments, scripts, absent/fake bundles rejected.
- Finder's special bundle type is allowed only for the expected system path and identifier.
- No fallback disables the sandbox or asks for broad access when an app is inaccessible.

## Remaining risks and limitations

- App Sandbox applies to the native runtime. The settings page runs in Stream Deck's property-inspector webview and follows the host's security boundary. It contains bundled HTML/JavaScript and no remote assets.
- Standard App Sandbox network-client permission is broader than loopback. A compromised binary could use outbound networking within that entitlement. Do not describe this as OS-enforced offline operation.
- The app can write inside its container and OS-permitted temporary locations. Normal runtime code does not need persistent storage, but the sandbox grants container storage by design.
- The local SDK connection has the host's registration mechanism, not separate cryptographic peer attestation. A malicious process already running as the user is not fully addressed by this design.
- A pinned app may itself be malicious. Validation is not malware scanning or publisher verification and does not eliminate filesystem replacement races. Apps launched through macOS are independent processes with their own permissions, not children inheriting DockDeck's sandbox.
- Reading standard application directories or mounted paths may involve OS services; this is not an OS-enforced zero-network system.
- Apps in private locations outside supported app folders may be omitted. Dock preferences are not a guaranteed stable API. Unpinned apps use launch order, not manually rearranged transient Dock order.
- App Sandbox does not validate the logic of app selection, profile return or UI correctness. Functional tests remain necessary.
- Developer ID signing/notarization, recipient-Mac tests, complete physical-device testing and independent audit remain release gates. See RELEASE.md.

## Verification

`tests/sandbox.py` compares signed production entitlements with the exact policy. It builds a separate probe with that same policy and checks a synthetic file outside its container cannot be read or overwritten, container storage works, Dock preferences can be read, and inbound bind is denied. This is concrete deny evidence, not proof that every possible sandbox escape is impossible.

`tests/integration.py` exercises the actual sandboxed production binary against a loopback host: registration, 14 PNG slots, profile commands, hostile settings, stale contexts and disconnect. The optional `--launch-finder` test brings Finder forward; it is not a physical button test. Model tests cover URL/path validation and app ordering. Packaging tests check profile structure and executable permissions.

References: [Apple App Sandbox](https://developer.apple.com/documentation/security/protecting-user-data-with-app-sandbox), [temporary read-only exceptions](https://developer.apple.com/library/archive/documentation/Miscellaneous/Reference/EntitlementKeyReference/Chapters/AppSandboxTemporaryExceptionEntitlements.html). No remote source code is bundled.
