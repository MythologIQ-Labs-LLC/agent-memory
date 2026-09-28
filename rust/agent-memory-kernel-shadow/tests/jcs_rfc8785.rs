use agent_memory_kernel_shadow::sha256_bytes;
use serde_json::Value;
use std::fs;
use std::path::PathBuf;

fn fixture_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../reference/fixtures/runtime-kernel/jcs-rfc8785-v1.json")
}

fn decode_hex(value: &str) -> Vec<u8> {
    assert_eq!(value.len() % 2, 0, "hex string must have even length");
    value
        .as_bytes()
        .chunks_exact(2)
        .map(|pair| {
            let text = std::str::from_utf8(pair).expect("hex is ASCII");
            u8::from_str_radix(text, 16).expect("valid hex byte")
        })
        .collect()
}

fn hex(bytes: &[u8]) -> String {
    let mut output = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        use std::fmt::Write as _;
        write!(&mut output, "{byte:02x}").expect("writing to String cannot fail");
    }
    output
}

#[test]
fn rust_rfc8785_matches_frozen_python_bytes_and_digests() {
    let fixture_text = fs::read_to_string(fixture_path()).expect("read frozen JCS fixture");
    let fixture: Value = serde_json::from_str(&fixture_text).expect("parse frozen JCS fixture");

    assert_eq!(fixture["profile"], "agent-memory-rfc8785-jcs-v1");
    assert_eq!(fixture["oracle"], "python rfc8785==0.1.4");
    assert_eq!(fixture["status"], "frozen-before-rust-jcs-execution");

    let cases = fixture["cases"].as_array().expect("cases array");
    assert_eq!(cases.len(), 5);

    for case in cases {
        let name = case["name"].as_str().expect("case name");
        let expected_hex = case["expected_utf8_hex"].as_str().expect("expected hex");
        let expected_bytes = decode_hex(expected_hex);
        let expected_sha256 = case["expected_sha256"].as_str().expect("expected digest");

        let canonical = serde_json_canonicalizer::to_vec(&case["value"])
            .unwrap_or_else(|error| panic!("{name}: RFC8785 serialization failed: {error}"));

        assert_eq!(canonical, expected_bytes, "{name}: canonical bytes differ");
        assert_eq!(hex(&sha256_bytes(&canonical)), expected_sha256, "{name}: SHA-256 differs");
    }
}
