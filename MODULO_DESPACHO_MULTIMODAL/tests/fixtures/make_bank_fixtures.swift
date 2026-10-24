// Generador de fixtures de comprobantes bancarios venezolanos anonimizados para pruebas E2E de OCR.
// Bancos soportados: Banco de Venezuela, Banesco, Bancamiga, Mercantil, BBVA Provincial.
// Compilación y ejecución: swiftc -O make_bank_fixtures.swift -o make_bank_fixtures && ./make_bank_fixtures

import AppKit
import CoreGraphics
import CoreText
import Foundation

struct BankVoucherSpec {
    let filename: String
    let bankTitle: String
    let lines: [String]
    let headerColor: (CGFloat, CGFloat, CGFloat)
}

let specs: [BankVoucherSpec] = [
    // 1. Banco de Venezuela (0102)
    BankVoucherSpec(
        filename: "voucher_bdv.png",
        bankTitle: "Banco de Venezuela - BDVenlinea",
        lines: [
            "Pago Movil BDV PagoClave",
            "Operacion: 0092837461",
            "Monto: Bs. 1.850,00",
            "Fecha: 19/10/2026",
            "Banco Emisor: 0102 Banco de Venezuela",
        ],
        headerColor: (0.85, 0.15, 0.20) // Rojo BDV
    ),
    // 2. Banesco (0134)
    BankVoucherSpec(
        filename: "voucher_banesco.png",
        bankTitle: "Banesco Banco Universal",
        lines: [
            "BanescoMovil - Recibo de Pago Movil",
            "Numero de Referencia: 0084729104",
            "Monto: Bs. 1.250,50",
            "Fecha: 19/10/2026",
            "Concepto: Recarga Movilnet",
        ],
        headerColor: (0.05, 0.45, 0.25) // Verde Banesco
    ),
    // 3. Bancamiga (0172)
    BankVoucherSpec(
        filename: "voucher_bancamiga.png",
        bankTitle: "Bancamiga Banco Universal",
        lines: [
            "Bancamiga Suite - Pago Movil",
            "Nro. Referencia: 017200876543",
            "Monto de la Operacion: Bs. 450,00",
            "Fecha: 19-10-2026",
            "Destino: Movilnet Prepago",
        ],
        headerColor: (0.10, 0.40, 0.70) // Azul Bancamiga
    ),
    // 4. Mercantil (0105)
    BankVoucherSpec(
        filename: "voucher_mercantil.png",
        bankTitle: "Mercantil Banco Universal",
        lines: [
            "Tpago Mercantil - Comprobante",
            "Numero de Referencia: 010500123456",
            "Total pagado: 320,00 Bs.",
            "Fecha: 19/10/2026",
            "Canal: Mercantil Movil",
        ],
        headerColor: (0.05, 0.25, 0.55) // Azul Oscuro Mercantil
    ),
    // 5. BBVA Provincial (0108)
    BankVoucherSpec(
        filename: "voucher_provincial.png",
        bankTitle: "BBVA Provincial",
        lines: [
            "Provinet Movil - Dinero Rapido",
            "N° Operacion: 010800345678",
            "Importe: 850,00 VES",
            "Fecha: 19/10/2026",
            "Estado: Transaccion Exitosa",
        ],
        headerColor: (0.02, 0.15, 0.40) // Azul Marino Provincial
    ),
]

let outDir = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "."

for spec in specs {
    let width = 950, height = 480
    let cs = CGColorSpaceCreateDeviceRGB()
    guard let ctx = CGContext(
        data: nil, width: width, height: height, bitsPerComponent: 8, bytesPerRow: 0,
        space: cs, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
    ) else {
        print("Error creando CGContext para \(spec.filename)")
        continue
    }

    // Fondo blanco limpio
    ctx.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1))
    ctx.fill(CGRect(x: 0, y: 0, width: width, height: height))

    // Barra de encabezado del banco
    let (r, g, b) = spec.headerColor
    ctx.setFillColor(CGColor(red: r, green: g, blue: b, alpha: 1))
    ctx.fill(CGRect(x: 0, y: height - 70, width: width, height: 70))

    // Título del encabezado (blanco)
    let headerFont = CTFontCreateWithName("Helvetica-Bold" as CFString, 32, nil)
    let headerAttrs: [NSAttributedString.Key: Any] = [
        .font: headerFont,
        .foregroundColor: CGColor(red: 1, green: 1, blue: 1, alpha: 1),
    ]
    let headerLine = CTLineCreateWithAttributedString(NSAttributedString(string: spec.bankTitle, attributes: headerAttrs))
    ctx.textPosition = CGPoint(x: 40, y: CGFloat(height) - 50)
    CTLineDraw(headerLine, ctx)

    // Contenido del voucher (texto negro de alta nitidez)
    let bodyFont = CTFontCreateWithName("Helvetica" as CFString, 44, nil)
    var y = CGFloat(height) - 150
    for line in spec.lines {
        let attrs: [NSAttributedString.Key: Any] = [
            .font: bodyFont,
            .foregroundColor: CGColor(red: 0, green: 0, blue: 0, alpha: 1),
        ]
        let ctLine = CTLineCreateWithAttributedString(NSAttributedString(string: line, attributes: attrs))
        ctx.textPosition = CGPoint(x: 40, y: y)
        CTLineDraw(ctLine, ctx)
        y -= 65
    }

    guard let image = ctx.makeImage() else { continue }
    let rep = NSBitmapImageRep(cgImage: image)
    guard let png = rep.representation(using: .png, properties: [:]) else { continue }

    let targetPath = (outDir as NSString).appendingPathComponent(spec.filename)
    do {
        try png.write(to: URL(fileURLWithPath: targetPath))
        print("✅ Generado: \(targetPath)")
    } catch {
        print("❌ Error escribiendo \(targetPath): \(error)")
    }
}
