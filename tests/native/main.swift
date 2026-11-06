import Foundation
let input = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]))
let object = try JSONSerialization.jsonObject(with: input) as! [String: Any]
let expected = Data(base64Encoded: object["jpeg"] as! String)!
let packets = object["packets"] as! [String]
let assembler = Camera757Assembler()
var frame: Camera757Frame?
for text in packets.reversed() {
 if let result = assembler.accept(Array(Data(base64Encoded: text)!), now: 100) { frame = result }
}
guard let frame, frame.jpeg == expected, frame.width == 640, frame.height == 360 else {
 fatalError("Existing V7RC Swift receiver rejected sender output")
}
print("PASS: existing V7RC SDK assembled \(packets.count) out-of-order fragments into byte-identical 640x360 full JPEG")
import ImageIO
import CoreFoundation
guard let source = CGImageSourceCreateWithData(frame.jpeg as CFData, nil),
      let image = CGImageSourceCreateImageAtIndex(source, 0, nil),
      image.width == 640, image.height == 360 else {
    fatalError("Apple ImageIO rejected the assembled JPEG")
}
print("PASS: Apple ImageIO decoded assembled JPEG as 640x360 pixels")
