import AppKit
// Fixed read-only observer for the explicit Finder activation integration test.
print(NSWorkspace.shared.frontmostApplication?.bundleIdentifier ?? "none")
