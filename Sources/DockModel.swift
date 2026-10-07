import AppKit

struct DockApp: Equatable {
    let url: URL
    let bundleID: String
    let name: String
}

enum DockModel {
    static let finder = URL(fileURLWithPath: "/System/Library/CoreServices/Finder.app")

    // No URL handlers, remote volumes, scripts, or arbitrary command execution.
    static func localAppURL(_ raw: String) -> URL? {
        guard raw.utf8.count <= 4096, !raw.contains("\0") else { return nil }
        let url: URL
        if raw.hasPrefix("/") { url = URL(fileURLWithPath: raw) }
        else {
            guard let parsed = URL(string: raw), parsed.isFileURL,
                  parsed.host == nil || parsed.host == "" || parsed.host == "localhost",
                  parsed.query == nil, parsed.fragment == nil else { return nil }
            url = parsed
        }
        let canonical = url.standardizedFileURL.resolvingSymlinksInPath()
        guard canonical.pathExtension.lowercased() == "app" else { return nil }
        return canonical
    }

    static func validate(_ url: URL) -> DockApp? {
        guard let safeURL = localAppURL(url.absoluteString),
              let values = try? safeURL.resourceValues(forKeys: [.isDirectoryKey, .volumeIsLocalKey]),
              values.isDirectory == true, values.volumeIsLocal == true,
              let bundle = Bundle(url: safeURL),
              let id = bundle.bundleIdentifier, !id.isEmpty,
              let executable = bundle.executableURL,
              FileManager.default.isExecutableFile(atPath: executable.path) else { return nil }
        let type = bundle.infoDictionary?["CFBundlePackageType"] as? String
        guard type == "APPL" || (type == "FNDR" && id == "com.apple.finder" && safeURL == finder.resolvingSymlinksInPath()) else { return nil }
        return DockApp(url: safeURL, bundleID: id,
                       name: FileManager.default.displayName(atPath: safeURL.path))
    }

    static func candidates(_ tiles: [[String: Any]], finder: URL = finder) -> [URL] {
        var result = [finder.standardizedFileURL.resolvingSymlinksInPath()]
        for tile in tiles.prefix(512) {
            guard tile["tile-type"] as? String == "file-tile",
                  let data = tile["tile-data"] as? [String: Any],
                  let file = data["file-data"] as? [String: Any],
                  let raw = file["_CFURLString"] as? String,
                  let url = localAppURL(raw), !result.contains(url) else { continue }
            result.append(url)
        }
        return result
    }

    static func read() -> [DockApp] {
        // Refresh the preferences cache; this process never sets any Dock preference.
        CFPreferencesSynchronize("com.apple.dock" as CFString,
                                kCFPreferencesCurrentUser, kCFPreferencesAnyHost)
        let tiles = CFPreferencesCopyAppValue("persistent-apps" as CFString,
                                             "com.apple.dock" as CFString) as? [[String: Any]] ?? []
        let recentTiles = CFPreferencesCopyAppValue("recent-apps" as CFString,
                                                   "com.apple.dock" as CFString) as? [[String: Any]] ?? []
        let showRecents = CFPreferencesCopyAppValue("show-recents" as CFString,
                                                   "com.apple.dock" as CFString) as? Bool ?? true
        let running = NSWorkspace.shared.runningApplications
            .filter { $0.activationPolicy == .regular && !$0.isTerminated }
            .sorted {
                let left = $0.launchDate ?? .distantPast
                let right = $1.launchDate ?? .distantPast
                return left == right ? $0.processIdentifier < $1.processIdentifier : left < right
            }.compactMap { $0.bundleURL?.standardizedFileURL.resolvingSymlinksInPath() }
        let pinned = candidates(tiles)
        let recent = showRecents ? Array(candidates(recentTiles).dropFirst()) : []
        return Array(orderedURLs(pinned: pinned, running: running, recent: recent)
            .compactMap(validate).prefix(14))
    }

    // The public running-app API does not expose Dock's manually rearranged transient order.
    // Callers supply launch order, while both persisted Dock sections retain their own order.
    static func orderedURLs(pinned: [URL], running: [URL], recent: [URL]) -> [URL] {
        let recentSet = Set(recent)
        let sequence = pinned + running.filter { !recentSet.contains($0) } + recent
        var seen = Set<URL>()
        return sequence.filter { seen.insert($0).inserted }
    }
}

struct Coordinates: Codable {
    let column: Int
    let row: Int
    var slot: Int? {
        guard (0..<5).contains(column), (0..<3).contains(row) else { return nil }
        let result = row * 5 + column
        return result < 14 ? result : nil
    }
}

struct DeckEvent: Decodable {
    struct Payload: Decodable {
        let settings: DockSettings?
        let coordinates: Coordinates?
        let controller: String?
        let isInMultiAction: Bool?
    }
    let event: String
    let context: String?
    let action: String?
    let device: String?
    let payload: Payload?
    let deviceInfo: DeviceInfo?
}

struct DeviceInfo: Decodable {
    let type: Int
}

struct LaunchArguments {
    let port: UInt16
    let uuid: String
    var mobileDevices: Set<String> = []
    static func parse(_ args: [String]) -> LaunchArguments? {
        guard args.count % 2 == 0 else { return nil }
        var values = [String: String]()
        for i in stride(from: 0, to: args.count, by: 2) {
            guard ["-port", "-pluginUUID", "-registerEvent", "-info"].contains(args[i]),
                  values[args[i]] == nil else { return nil }
            values[args[i]] = args[i + 1]
        }
        guard let raw = values["-port"], let port = UInt16(raw), port > 0,
              let uuid = values["-pluginUUID"], !uuid.isEmpty, uuid.utf8.count <= 256,
              values["-registerEvent"] == "registerPlugin" else { return nil }
        let info = values["-info"].flatMap { $0.data(using: .utf8) }.flatMap { try? JSONSerialization.jsonObject(with: $0) } as? [String: Any]
        let devices = info?["devices"] as? [[String: Any]] ?? []
        let mobile = Set(devices.filter { $0["type"] as? Int == 3 }.compactMap { $0["id"] as? String })
        return LaunchArguments(port: port, uuid: uuid, mobileDevices: mobile)
    }
}

struct DockSettings: Decodable {
    let autoReturnSeconds: Double
    enum CodingKeys: String, CodingKey { case autoReturnSeconds }
    init(from decoder: Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        let seconds = (try? values.decode(Double.self, forKey: .autoReturnSeconds)) ?? 0
        autoReturnSeconds = seconds.isFinite && seconds >= 0 && seconds <= 86400 ? seconds : 0
    }
}
