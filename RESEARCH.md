# Existing implementations reviewed

Research date: 2026-09-16. GitHub and Elgato Marketplace web searches did not identify a verified exact match for pinned Dock order → 14 app keys + one return key. This is a bounded search result, not proof that no such plugin exists.

| Project | Finding | Decision |
| --- | --- | --- |
| [JarnoLeConte/streamdeck-appswitcher](https://github.com/JarnoLeConte/streamdeck-appswitcher) | Cycles recent apps by synthesizing Command-Tab with AppleScript/System Events. The source explicitly initializes System Events access. | Existing plugin, but no Dock grid; avoid Apple Events/input synthesis. |
| [BowerStudio/Snap-Launcher](https://github.com/BowerStudio/Snap-Launcher) | Per-key app launch/focus and window placement; macOS backend invokes osascript/JXA. README documents Accessibility permission for window control. | Broader than needed. No source copied or dependency added. |
| [kcrawford/dockutil](https://github.com/kcrawford/dockutil) | Reads pinned Dock tiles using `CFPreferencesCopyAppValue`, with tile file URL parsing; also offers Dock modification capabilities. | Reference for Dock data shape and preference reads only; no write/kill/restart logic used. |

Reviewed exact commits:

- dockutil: `7238012dc414eed1604f0ce8791937c493e1f914` — `Sources/DockUtil/Dock.swift`, `DockTile.swift` (Apache-2.0).
- App Switcher: `5b73889ffbf5ce20127d3c9d7f901c79a9b10527` — `Sources/Plugin.swift` (MIT).
- Snap Launcher: `bb5e0b4109a4bb270d2315c9bc94ed0ff4a8ceca` — `src/platform/macos/osascript.ts`, macOS backend and README. No top-level LICENSE file found in this checkout; no reuse assumed.

Repositories were cloned into ignored `research/` for inspection only. Their installers, scripts, build tasks and dependencies were not run. DockDeck uses new implementation code and ships none of these repositories.

Official references:

- [Elgato native WebSocket registration, setImage and switchToProfile](https://docs.elgato.com/streamdeck/sdk/references/websocket/plugin/).
- [Elgato bundled profiles](https://docs.elgato.com/streamdeck/sdk/guides/profiles/).
- [Elgato manifest](https://docs.elgato.com/streamdeck/sdk/references/manifest/).
- [Apple NSWorkspace](https://developer.apple.com/documentation/appkit/nsworkspace).

The generated profile's archive structure was checked against the default profile shipped with the installed official Stream Deck app. No user profile contents, app icons, device serials or credentials are included in the distributable. Only generic layout metadata and original generated UI assets are bundled.
