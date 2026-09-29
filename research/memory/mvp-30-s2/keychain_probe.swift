import Foundation
import Security

func fail(_ message: String, _ code: Int32) -> Never {
    FileHandle.standardError.write(Data((message + "\n").utf8))
    exit(code)
}

guard CommandLine.arguments.count == 4 else {
    fail("usage: keychain_probe <add|read|delete> <service> <account>", 64)
}

let operation = CommandLine.arguments[1]
let service = CommandLine.arguments[2]
let account = CommandLine.arguments[3]

var base: [String: Any] = [
    kSecClass as String: kSecClassGenericPassword,
    kSecAttrService as String: service,
    kSecAttrAccount as String: account,
]

switch operation {
case "add":
    var bytes = [UInt8](repeating: 0, count: 32)
    let randomStatus = SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes)
    guard randomStatus == errSecSuccess else {
        fail("SecRandomCopyBytes status=\(randomStatus)", 65)
    }

    // The generated value exists only in process memory and Keychain Services.
    // It is never printed, written to argv/environment, or stored in a file.
    var query = base
    query[kSecValueData as String] = Data(bytes)

    let status = SecItemAdd(query as CFDictionary, nil)
    guard status == errSecSuccess else {
        fail("SecItemAdd status=\(status)", 66)
    }
    exit(0)

case "read":
    var query = base
    query[kSecReturnData as String] = kCFBooleanTrue
    query[kSecMatchLimit as String] = kSecMatchLimitOne

    var result: CFTypeRef?
    let status = SecItemCopyMatching(query as CFDictionary, &result)
    guard status == errSecSuccess else {
        fail("SecItemCopyMatching status=\(status)", 67)
    }
    guard result is Data else {
        fail("SecItemCopyMatching returned unexpected result type", 68)
    }
    // Deliberately do not emit the secret value.
    exit(0)

case "delete":
    let status = SecItemDelete(base as CFDictionary)
    guard status == errSecSuccess || status == errSecItemNotFound else {
        fail("SecItemDelete status=\(status)", 69)
    }
    exit(0)

default:
    fail("unknown operation", 64)
}
