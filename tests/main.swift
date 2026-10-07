import Foundation

var count = 0
func check(_ condition: @autoclosure () -> Bool, _ label: String) {
    guard condition() else { fatalError("FAILED: " + label) }
    count += 1
}
check(DockModel.localAppURL("https://example.com/Fake.app") == nil, "reject web URL")
check(DockModel.localAppURL("file://remote-server/Applications/Fake.app") == nil, "reject remote host")
check(DockModel.localAppURL("smb://server/Fake.app") == nil, "reject SMB")
check(DockModel.localAppURL("/tmp/test.sh") == nil, "reject scripts")
check(DockModel.localAppURL("file:///Applications/Test.app?command=1") == nil, "reject query")
check(DockModel.localAppURL("file:///Applications/Test.app#x") == nil, "reject fragment")
check(DockModel.localAppURL("/tmp/Bad\0.app") == nil, "reject NUL")
check(DockModel.localAppURL("file:///Applications/Some%20App.app/")?.path == "/Applications/Some App.app", "decode spaces")
check(DockModel.validate(URL(fileURLWithPath: "/tmp/nonexistent.app")) == nil, "reject absent bundle")
check(DockModel.validate(DockModel.finder)?.bundleID == "com.apple.finder", "validate system Finder")
let temp = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString + ".app")
try FileManager.default.createDirectory(at: temp, withIntermediateDirectories: true)
defer { try? FileManager.default.removeItem(at: temp) }
check(DockModel.validate(temp) == nil, "reject directory pretending to be app")
func tile(_ path: String, type: String = "file-tile") -> [String: Any] {
    ["tile-type": type, "tile-data": ["file-data": ["_CFURLString": path]]]
}
let candidates = DockModel.candidates([
    tile("file:///Applications/One.app"), tile("file:///Applications/One.app"),
    tile("https://example.com/Bad.app"), tile("/Applications/Spacer.app", type: "spacer-tile"),
    tile("/Applications/Two.app"), tile(DockModel.finder.absoluteString)])
check(candidates.count == 3, "deduplicate, skip invalid tiles, include Finder once")
check(candidates[1].lastPathComponent == "One.app" && candidates[2].lastPathComponent == "Two.app", "preserve order")
check(Coordinates(column: 3, row: 2).slot == 13, "14th app")
check(Coordinates(column: 4, row: 2).slot == nil, "exit has no app")
check(Coordinates(column: -1, row: 0).slot == nil, "reject negative position")
check(Coordinates(column: 5, row: 0).slot == nil, "reject oversized position")
let args = ["-port", "12345", "-pluginUUID", "test", "-registerEvent", "registerPlugin"]
check(LaunchArguments.parse(args)?.port == 12345, "valid registration")
check(LaunchArguments.parse(["-port", "99999"] + Array(args.dropFirst(2))) == nil, "reject invalid port")
check(LaunchArguments.parse(args + ["-host", "example.com"]) == nil, "reject remote host option")
check(LaunchArguments.parse(args + ["-port", "2"]) == nil, "reject duplicate flags")
check(LaunchArguments.parse(Array(args.dropLast())) == nil, "reject incomplete arguments")
print("Passed \(count) model/security checks")
let a = URL(fileURLWithPath: "/Applications/A.app")
let b = URL(fileURLWithPath: "/Applications/B.app")
let c = URL(fileURLWithPath: "/Applications/C.app")
let d = URL(fileURLWithPath: "/Applications/D.app")
check(DockModel.orderedURLs(pinned: [a], running: [a, b, c], recent: [c, d]) == [a, b, c, d], "running then recent; deduplicate")
check(DockModel.orderedURLs(pinned: [a, c], running: [b, a, c], recent: [c, d]) == [a, c, b, d], "pinned order takes precedence")
check(DockModel.orderedURLs(pinned: [a], running: [c, b], recent: []) == [a, c, b], "recent disabled retains running order")
check(DockModel.orderedURLs(pinned: [a], running: [], recent: [d, c]) == [a, d, c], "closed recent apps retain preference order")
print("Passed \(count) total model/security/order checks")
