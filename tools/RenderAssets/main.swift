import AppKit

    let directory = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    for (name, size, symbol) in [("key", 72, "square.grid.3x3.fill"), ("key@2x", 144, "square.grid.3x3.fill"),
                                ("exit", 72, "arrow.uturn.backward"), ("exit@2x", 144, "arrow.uturn.backward"),
                                ("plugin", 256, "square.grid.3x3.fill"), ("plugin@2x", 512, "square.grid.3x3.fill")] {
        try IconRenderer.png(app: nil, symbol: symbol, size: size).write(to: directory.appendingPathComponent(name + ".png"))
    }
