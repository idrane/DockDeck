import AppKit

let pluginID = "local.dockdeck"

@MainActor final class DockDeck {
    struct Key {
        let action: String
        let device: String
        let slot: Int?
        var displayed: DockApp?
        var imageKey: String = ""
        var autoReturnSeconds: Double = 0
    }
    let registration: LaunchArguments
    let session: URLSession
    let socket: URLSessionWebSocketTask
    var mobileDevices: Set<String>
    var keys = [String: Key]()
    var apps = [DockApp]()
    var iconCache = [String: String]()
    var observers = [NSObjectProtocol]()
    var timer: Timer?
    var output = [String]()
    var sending = false
    var pendingReturn = [String: Double]()
    var returnTimers = [String: Timer]()
    var returnDeadlines = [String: TimeInterval]()

    init(_ registration: LaunchArguments) {
        self.registration = registration
        mobileDevices = registration.mobileDevices
        let config = URLSessionConfiguration.ephemeral
        config.connectionProxyDictionary = [:]
        config.httpCookieStorage = nil
        config.urlCache = nil
        config.timeoutIntervalForRequest = 10
        session = URLSession(configuration: config)
        // The host is hard-coded: command line arguments cannot select a remote endpoint.
        socket = session.webSocketTask(with: URL(string: "ws://127.0.0.1:\(registration.port)")!)
        socket.maximumMessageSize = 65536
    }

    func send(_ object: [String: Any]) {
        guard let data = try? JSONSerialization.data(withJSONObject: object),
              let text = String(data: data, encoding: .utf8) else { return }
        guard output.count < 256 else { stop() }
        output.append(text)
        guard !sending else { return }
        sending = true
        Task { @MainActor in
            do {
                while !output.isEmpty { try await socket.send(.string(output.removeFirst())) }
                sending = false
            } catch { stop() }
        }
    }

    func stop() -> Never {
        socket.cancel(with: .goingAway, reason: nil)
        session.invalidateAndCancel()
        exit(0)
    }

    func start() {
        socket.resume()
        send(["event": "registerPlugin", "uuid": registration.uuid])
        Task { @MainActor in
            do {
                while true {
                    let message = try await socket.receive()
                    let data: Data
                    switch message {
                    case .string(let value): data = Data(value.utf8)
                    case .data(let value): data = value
                    @unknown default: continue
                    }
                    if data.count <= 65536, let event = try? JSONDecoder().decode(DeckEvent.self, from: data) {
                        handle(event)
                    }
                }
            } catch { stop() }
        }
        for name in [NSWorkspace.didLaunchApplicationNotification, NSWorkspace.didTerminateApplicationNotification,
                     NSWorkspace.didActivateApplicationNotification, NSWorkspace.didWakeNotification] {
            observers.append(NSWorkspace.shared.notificationCenter.addObserver(forName: name, object: nil, queue: .main) { [weak self] _ in
                Task { @MainActor in self?.refresh(readDock: true) }
            })
        }
        timer = Timer.scheduledTimer(withTimeInterval: 2, repeats: true) { [weak self] _ in
            Task { @MainActor in self?.refresh(readDock: true) }
        }
    }

    func handle(_ event: DeckEvent) {
        if event.event == "deviceDidConnect", let device = event.device, let info = event.deviceInfo {
            if info.type == 3 { mobileDevices.insert(device) } else { mobileDevices.remove(device) }
            return
        }
        if event.event == "deviceDidDisconnect", let device = event.device {
            cancelReturn(device)
            keys = keys.filter { $0.value.device != device }; mobileDevices.remove(device); return
        }
        guard let context = event.context, context.utf8.count <= 256 else { return }
        if event.event == "willDisappear" {
            if let key = keys.removeValue(forKey: context), key.action == "\(pluginID).exit" { cancelReturn(key.device) }
            return
        }
        guard let action = event.action, ["\(pluginID).open", "\(pluginID).slot", "\(pluginID).exit"].contains(action),
              let device = event.device, device.utf8.count <= 256,
              event.payload?.isInMultiAction != true,
              event.payload?.controller == nil || event.payload?.controller == "Keypad" else { return }
        if event.event == "willAppear" {
            guard keys.count < 64 || keys[context] != nil else { return }
            keys[context] = Key(action: action, device: device, slot: event.payload?.coordinates?.slot)
            keys[context]?.autoReturnSeconds = event.payload?.settings?.autoReturnSeconds ?? 0
            if action == "\(pluginID).exit", let seconds = pendingReturn.removeValue(forKey: device), seconds > 0 {
                returnTimers[device]?.invalidate()
                returnDeadlines[device] = ProcessInfo.processInfo.systemUptime + seconds
                returnTimers[device] = Timer.scheduledTimer(withTimeInterval: min(0.1, seconds), repeats: true) { [weak self] _ in
                    Task { @MainActor in
                        guard let self, self.keys[context]?.action == "\(pluginID).exit" else { return }
                        if ProcessInfo.processInfo.systemUptime >= (self.returnDeadlines[device] ?? 0) {
                            self.returnToPrevious(device)
                        } else {
                            self.refresh(readDock: false)
                        }
                    }
                }
            }
            refresh(readDock: true)
        } else if event.event == "didReceiveSettings" {
            keys[context]?.autoReturnSeconds = event.payload?.settings?.autoReturnSeconds ?? 0
        } else if event.event == "keyDown", let key = keys[context], key.action == action, key.device == device {
            if action == "\(pluginID).open" {
                cancelReturn(device)
                pendingReturn[device] = event.payload?.settings?.autoReturnSeconds ?? key.autoReturnSeconds
                send(["event": "switchToProfile", "context": registration.uuid, "device": device,
                      "payload": ["profile": mobileDevices.contains(device) ? "Dock14Mobile" : "Dock14", "page": 0]])
            } else if action == "\(pluginID).exit" {
                returnToPrevious(device)
            } else if let displayed = key.displayed {
                // Launch the app represented by the displayed image, never an untrusted settings path.
                guard let validated = DockModel.validate(displayed.url), validated == displayed else {
                    alert(context); refresh(readDock: true); return
                }
                let configuration = NSWorkspace.OpenConfiguration()
                configuration.activates = true
                configuration.addsToRecentItems = false
                configuration.createsNewApplicationInstance = false
                NSWorkspace.shared.openApplication(at: validated.url, configuration: configuration) { [weak self] _, error in
                    if let error { Task { @MainActor in
                        self?.alert(context)
                        self?.send(["event": "logMessage", "payload": ["message": "DockDeck: app activation failed; OS error code \((error as NSError).code)."]])
                    } }
                }
            } else { alert(context) }
        }
    }

    func cancelReturn(_ device: String) {
        returnTimers.removeValue(forKey: device)?.invalidate()
        pendingReturn.removeValue(forKey: device)
        returnDeadlines.removeValue(forKey: device)
    }

    func returnToPrevious(_ device: String) {
        cancelReturn(device)
        send(["event": "switchToProfile", "context": registration.uuid, "device": device,
              "payload": [String: String]()])
    }

    func alert(_ context: String) { send(["event": "showAlert", "context": context]) }

    func refresh(readDock: Bool) {
        guard !keys.isEmpty else { return }
        if readDock && keys.values.contains(where: { $0.action == "\(pluginID).slot" }) {
            let updated = DockModel.read()
            if updated != apps { apps = updated; iconCache.removeAll() }
        }
        let running = Set(NSWorkspace.shared.runningApplications.compactMap { $0.bundleURL?.resolvingSymlinksInPath().path })
        let active = NSWorkspace.shared.frontmostApplication?.bundleURL?.resolvingSymlinksInPath().path
        for context in Array(keys.keys) {
            guard var key = keys[context] else { continue }
            let app = key.action == "\(pluginID).slot" ? key.slot.flatMap { apps.indices.contains($0) ? apps[$0] : nil } : nil
            let symbol = key.action == "\(pluginID).open" ? "square.grid.3x3.fill" : key.action == "\(pluginID).exit" ? "arrow.uturn.backward" : nil
            let isRunning = app.map { running.contains($0.url.path) } ?? false
            let isActive = app.map { active == $0.url.path } ?? false
            let countdown = key.action == "\(pluginID).exit" ? returnDeadlines[key.device].map { max(1, Int(ceil($0 - ProcessInfo.processInfo.systemUptime))) } : nil
            let imageKey = "\(app?.url.path ?? symbol ?? "empty")|\(isRunning)|\(isActive)|\(countdown ?? 0)"
            guard key.imageKey != imageKey else { continue }
            let image = iconCache[imageKey] ?? "data:image/png;base64," + IconRenderer.png(app: app, running: isRunning, active: isActive, symbol: symbol, countdown: countdown).base64EncodedString()
            if iconCache.count > 80 { iconCache.removeAll() }
            iconCache[imageKey] = image
            key.displayed = app; key.imageKey = imageKey; keys[context] = key
            send(["event": "setImage", "context": context, "payload": ["image": image, "target": 0]])
            send(["event": "setTitle", "context": context, "payload": ["title": "", "target": 0]])
        }
    }
}

let arguments = Array(CommandLine.arguments.dropFirst())
if arguments == ["--snapshot"] {
    // Explicit read-only diagnostic: never launches apps or opens a connection.
    let apps = DockModel.read()
    let output = apps.enumerated().map { ["slot": String($0.offset + 1), "name": $0.element.name, "bundleID": $0.element.bundleID] }
    let data = try JSONSerialization.data(withJSONObject: output, options: [.prettyPrinted, .sortedKeys])
    print(String(decoding: data, as: UTF8.self))
} else if let registration = LaunchArguments.parse(arguments) {
    let app = NSApplication.shared
    app.setActivationPolicy(.prohibited)
    MainActor.assumeIsolated {
        let plugin = DockDeck(registration)
        plugin.start()
        withExtendedLifetime(plugin) { app.run() }
    }
} else {
    fputs("DockDeck: launch through Stream Deck, or use --snapshot for a read-only check.\n", stderr)
    exit(64)
}
