// Genera un comprobante SINTÉTICO (sin datos reales de ninguna persona) como PNG para pruebas E2E de OCR.
// Uso: swiftc -O tests/fixtures/make_voucher_fixture.swift -o /tmp/mkvoucher && /tmp/mkvoucher tests/fixtures/voucher_sintetico.png
import AppKit
import CoreGraphics
import CoreText
import Foundation

let outPath = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "voucher_sintetico.png"
let lines = [
    "Pago Movil Banesco",
    "Referencia: 0084729104",
    "Monto: Bs. 1.250,50",
    "Fecha: 18/10/2026",
]
let width = 900, height = 420
let cs = CGColorSpaceCreateDeviceRGB()
guard let ctx = CGContext(data: nil, width: width, height: height, bitsPerComponent: 8, bytesPerRow: 0,
                          space: cs, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { exit(1) }
ctx.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1))
ctx.fill(CGRect(x: 0, y: 0, width: width, height: height))
let font = CTFontCreateWithName("Helvetica" as CFString, 48, nil)
var y = CGFloat(height) - 90
for line in lines {
    let attrs: [NSAttributedString.Key: Any] = [
        .font: font,
        .foregroundColor: CGColor(red: 0, green: 0, blue: 0, alpha: 1),
    ]
    let ctLine = CTLineCreateWithAttributedString(NSAttributedString(string: line, attributes: attrs))
    ctx.textPosition = CGPoint(x: 40, y: y)
    CTLineDraw(ctLine, ctx)
    y -= 85
}
guard let image = ctx.makeImage() else { exit(1) }
let rep = NSBitmapImageRep(cgImage: image)
guard let png = rep.representation(using: .png, properties: [:]) else { exit(1) }
try png.write(to: URL(fileURLWithPath: outPath))
print("fixture escrito en \(outPath)")
