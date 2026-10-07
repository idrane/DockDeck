import AppKit
import Darwin

let sentinel = URL(fileURLWithPath: CommandLine.arguments[1])
var results = [String: Bool]()
do { _ = try Data(contentsOf: sentinel); results["outsideReadDenied"] = false }
catch { results["outsideReadDenied"] = true }
do { try Data("must-not-write".utf8).write(to: sentinel); results["outsideWriteDenied"] = false }
catch { results["outsideWriteDenied"] = true }
let own = URL(fileURLWithPath: NSHomeDirectory()).appendingPathComponent("dockdeck-probe-" + UUID().uuidString)
do {
    try Data("container-only".utf8).write(to: own)
    results["containerWriteAllowed"] = true
    try FileManager.default.removeItem(at: own)
} catch { results["containerWriteAllowed"] = false }
results["containerHome"] = NSHomeDirectory().contains("/Library/Containers/")
let dock = CFPreferencesCopyAppValue("persistent-apps" as CFString, "com.apple.dock" as CFString) as? [[String: Any]]
results["dockPreferencesReadable"] = dock != nil
let fd = socket(AF_INET, SOCK_STREAM, 0)
var address = sockaddr_in()
address.sin_len = UInt8(MemoryLayout<sockaddr_in>.size)
address.sin_family = sa_family_t(AF_INET)
address.sin_addr.s_addr = inet_addr("127.0.0.1")
let bound = withUnsafePointer(to: &address) { pointer in
    pointer.withMemoryRebound(to: sockaddr.self, capacity: 1) { bind(fd, $0, socklen_t(MemoryLayout<sockaddr_in>.size)) }
}
results["inboundListenDenied"] = bound != 0
if fd >= 0 { close(fd) }
let data = try JSONSerialization.data(withJSONObject: results, options: [.sortedKeys])
print(String(decoding: data, as: UTF8.self))
exit(results.values.allSatisfy { $0 } ? 0 : 1)
