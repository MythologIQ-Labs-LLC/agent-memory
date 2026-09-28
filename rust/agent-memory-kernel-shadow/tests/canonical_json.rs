#[path = "../src/canonical_json.rs"]
mod canonical_json;

use agent_memory_kernel_shadow::sha256_bytes;
use canonical_json::{canonical_bytes, CanonicalValue};
use std::collections::BTreeMap;
use std::fs;
use std::path::PathBuf;

fn fixture_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../reference/fixtures/runtime-kernel/canonical-json-nonfloat-v1.tsv")
}

fn object(entries: Vec<(&str, CanonicalValue)>) -> CanonicalValue {
    CanonicalValue::Object(
        entries
            .into_iter()
            .map(|(key, value)| (key.to_owned(), value))
            .collect::<BTreeMap<_, _>>(),
    )
}

fn string(value: &str) -> CanonicalValue {
    CanonicalValue::String(value.to_owned())
}

fn case_value(case: &str) -> CanonicalValue {
    match case {
        "scalars" => object(vec![
            ("z", CanonicalValue::Null),
            ("n", CanonicalValue::Integer(42)),
            ("m", CanonicalValue::Integer(-7)),
            ("b", CanonicalValue::Bool(true)),
            ("a", CanonicalValue::Bool(false)),
        ]),
        "unicode" => object(vec![
            ("greeting", string("héllo 🌨️")),
            ("empty", string("")),
            ("city", string("München")),
        ]),
        "nested" => object(vec![
            (
                "c",
                CanonicalValue::Array(vec![
                    object(vec![("k", string("v"))]),
                    CanonicalValue::Null,
                    CanonicalValue::Bool(false),
                ]),
            ),
            (
                "b",
                CanonicalValue::Array(vec![
                    CanonicalValue::Integer(3),
                    CanonicalValue::Integer(2),
                    CanonicalValue::Integer(1),
                ]),
            ),
            ("a", object(vec![("y", string("yes")), ("x", string("no"))])),
        ]),
        "escaping" => object(vec![
            ("slash", string("a\\b")),
            ("quote", string("a\"b")),
            ("control", string("line\nbreak\tend")),
        ]),
        "ints" => object(vec![
            ("positive", CanonicalValue::Integer(12_345_678_901_234_567_890)),
            ("zero", CanonicalValue::Integer(0)),
            ("negative", CanonicalValue::Integer(-123_456_789)),
        ]),
        other => panic!("unknown canonical fixture case: {other}"),
    }
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
fn frozen_nonfloat_canonical_json_matches_python_bytes_and_digest() {
    let source = fs::read_to_string(fixture_path()).expect("read canonical JSON fixture");
    let mut count = 0;

    for line in source.lines().skip(1).filter(|line| !line.is_empty()) {
        let fields: Vec<&str> = line.splitn(4, '\t').collect();
        assert_eq!(fields.len(), 4, "malformed canonical fixture row: {line}");
        let case = fields[0];
        let expected = fields[2].as_bytes();
        let expected_sha = fields[3];

        let actual = canonical_bytes(&case_value(case));
        assert_eq!(actual, expected, "canonical byte mismatch for {case}");
        assert_eq!(hex(&sha256_bytes(&actual)), expected_sha, "canonical digest mismatch for {case}");
        count += 1;
    }

    assert_eq!(count, 5);
}
