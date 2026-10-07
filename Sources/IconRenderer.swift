import AppKit

enum IconRenderer {
    static func png(app: DockApp?, running: Bool = false, active: Bool = false,
                    symbol: String? = nil, countdown: Int? = nil, size: Int = 144) -> Data {
        let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: size, pixelsHigh: size,
                                      bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true,
                                      isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
        NSGraphicsContext.saveGraphicsState()
        NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: bitmap)
        let scale = CGFloat(size) / 144
        let transform = NSAffineTransform(); transform.scale(by: scale); transform.concat()
        NSColor(calibratedWhite: 0.045, alpha: 1).setFill()
        NSBezierPath(rect: NSRect(x: 0, y: 0, width: 144, height: 144)).fill()
        if active {
            NSColor.systemCyan.setStroke()
            let border = NSBezierPath(roundedRect: NSRect(x: 4, y: 4, width: 136, height: 136), xRadius: 19, yRadius: 19)
            border.lineWidth = 5; border.stroke()
        }
        if let app {
            NSWorkspace.shared.icon(forFile: app.url.path).draw(in: NSRect(x: 16, y: 22, width: 112, height: 112))
        } else if let symbol, let image = NSImage(systemSymbolName: symbol, accessibilityDescription: nil) {
            let configuration = NSImage.SymbolConfiguration(pointSize: 70, weight: .medium)
                .applying(.init(paletteColors: [.white]))
            let tinted = image.withSymbolConfiguration(configuration) ?? image
            NSAppearance(named: .darkAqua)?.performAsCurrentDrawingAppearance {
                tinted.draw(in: countdown == nil ? NSRect(x: 30, y: 30, width: 84, height: 84) : NSRect(x: 54, y: 10, width: 36, height: 36))
            }
        }
        if let countdown {
            let text = String(countdown) as NSString
            let attributes: [NSAttributedString.Key: Any] = [
                .font: NSFont.monospacedDigitSystemFont(ofSize: countdown < 100 ? 76 : countdown < 1000 ? 58 : 38, weight: .semibold),
                .foregroundColor: NSColor.white
            ]
            let bounds = text.size(withAttributes: attributes)
            text.draw(at: NSPoint(x: (144 - bounds.width) / 2, y: 48), withAttributes: attributes)
        }
        if running {
            (active ? NSColor.systemCyan : NSColor.white).setFill()
            NSBezierPath(ovalIn: NSRect(x: 67, y: 6, width: 10, height: 10)).fill()
        }
        NSGraphicsContext.restoreGraphicsState()
        return bitmap.representation(using: .png, properties: [:])!
    }
}
