// Módulo Autónomo de Despacho Multimodal — Helper OCR nativo de macOS (framework Vision).
// Lee los BYTES de una imagen por stdin y escribe el texto reconocido (una línea por renglón) en stdout.
// Zero-PII: no escribe nada en disco. Sin dependencias externas (solo frameworks del sistema).
// Códigos de salida: 0 OK · 2 imagen inválida · 3 error de Vision.
//
// Compilar (lo hace automáticamente infrastructure/ocr_backends.py):
//   swiftc -O infrastructure/apple_vision_ocr.swift -o .cache/apple_vision_ocr

import Foundation
import ImageIO
import Vision

let inputData = FileHandle.standardInput.readDataToEndOfFile()

guard
    let source = CGImageSourceCreateWithData(inputData as CFData, nil),
    let cgImage = CGImageSourceCreateImageAtIndex(source, 0, nil)
else {
    FileHandle.standardError.write("imagen inválida o formato no soportado\n".data(using: .utf8)!)
    exit(2)
}

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
// La corrección de lenguaje puede "arreglar" dígitos de referencias y montos: se desactiva.
request.usesLanguageCorrection = false

// Idiomas deseados, filtrados contra los realmente soportados por este macOS.
let wanted = ["es-ES", "en-US"]
if let supported = try? request.supportedRecognitionLanguages() {
    let usable = wanted.filter { supported.contains($0) }
    if !usable.isEmpty { request.recognitionLanguages = usable }
}

do {
    try VNImageRequestHandler(cgImage: cgImage, options: [:]).perform([request])
} catch {
    FileHandle.standardError.write("error de Vision: \(error)\n".data(using: .utf8)!)
    exit(3)
}

let observations = (request.results ?? []).sorted { $0.boundingBox.maxY > $1.boundingBox.maxY }
for observation in observations {
    if let candidate = observation.topCandidates(1).first {
        print(candidate.string)
    }
}
