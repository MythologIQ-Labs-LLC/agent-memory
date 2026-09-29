#[path = "../src/canonical_json_v2.rs"]
mod canonical_json_v2;

use canonical_json_v2::{
    canonical_bytes_v2, canonicalize_json_text_v2, string_from_codepoints_v2,
    CanonicalJsonV2Error, CanonicalValueV2,
};
use serde_json::Value;
use std::fs;
use std::path::PathBuf;

fn fixture_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../reference/fixtures/runtime/canonical-json-v2-vectors-v1.json")
}

fn acceptance_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../reference/fixtures/runtime/canonical-json-v2-vectors-accepted-v1.json")
}

fn from_json_value(value: &Value) -> CanonicalValueV2 {
    match value {
        Value::Null => CanonicalValueV2::Null,
        Value::Bool(value) => CanonicalValueV2::Bool(*value),
        Value::Number(value) => {
            if let Some(integer) = value.as_i64() {
                CanonicalValueV2::Integer(integer as i128)
            } else if let Some(integer) = value.as_u64() {
                CanonicalValueV2::Integer(integer as i128)
            } else {
                CanonicalValueV2::Float(value.as_f64().expect("fixture number is representable as f64"))
            }
        }
        Value::String(value) => CanonicalValueV2::String(value.clone()),
        Value::Array(values) => CanonicalValueV2::Array(values.iter().map(from_json_value).collect()),
        Value::Object(values) => CanonicalValueV2::Object(
            values
                .iter()
                .map(|(key, value)| (key.clone(), from_json_value(value)))
                .collect(),
        ),
    }
}

fn binary64(bits: &str) -> f64 {
    f64::from_bits(u64::from_str_radix(bits, 16).expect("binary64 fixture hex"))
}

fn run_case(case: &Value) -> Result<Vec<u8>, CanonicalJsonV2Error> {
    let input = &case["input"];
    let kind = input["kind"].as_str().expect("fixture input kind");
    match kind {
        "null" => canonical_bytes_v2(&CanonicalValueV2::Null),
        "bool" => canonical_bytes_v2(&CanonicalValueV2::Bool(
            input["value"].as_bool().expect("bool fixture"),
        )),
        "string" => canonical_bytes_v2(&CanonicalValueV2::String(
            input["value"].as_str().expect("string fixture").to_owned(),
        )),
        "string_codepoints" => {
            let codepoints: Vec<u32> = input["hex"]
                .as_array()
                .expect("codepoint array")
                .iter()
                .map(|item| {
                    u32::from_str_radix(item.as_str().expect("codepoint hex"), 16)
                        .expect("valid codepoint hex")
                })
                .collect();
            let value = string_from_codepoints_v2(&codepoints)?;
            canonical_bytes_v2(&CanonicalValueV2::String(value))
        }
        "int" => {
            let integer: i128 = input["decimal"]
                .as_str()
                .expect("integer decimal string")
                .parse()
                .map_err(|_| CanonicalJsonV2Error::IntegerOutOfRange)?;
            canonical_bytes_v2(&CanonicalValueV2::Integer(integer))
        }
        "binary64_bits" => canonical_bytes_v2(&CanonicalValueV2::Float(binary64(
            input["hex"].as_str().expect("binary64 bits"),
        ))),
        "json_value" => canonical_bytes_v2(&from_json_value(&input["value"])),
        "object_entries" => {
            let entries = input["entries"]
                .as_array()
                .expect("object entries")
                .iter()
                .map(|entry| {
                    let pair = entry.as_array().expect("object entry pair");
                    (
                        pair[0].as_str().expect("string object key").to_owned(),
                        from_json_value(&pair[1]),
                    )
                })
                .collect();
            canonical_bytes_v2(&CanonicalValueV2::Object(entries))
        }
        "object_entries_typed" => Err(CanonicalJsonV2Error::NonStringObjectKey),
        "json_text" => canonicalize_json_text_v2(input["text"].as_str().expect("json text fixture")),
        other => panic!("unexpected fixture input kind: {other}"),
    }
}

#[test]
fn accepted_source_is_the_only_v2_oracle() {
    let fixture: Value = serde_json::from_str(&fs::read_to_string(fixture_path()).expect("read fixture"))
        .expect("parse fixture");
    let acceptance: Value =
        serde_json::from_str(&fs::read_to_string(acceptance_path()).expect("read acceptance"))
            .expect("parse acceptance");

    assert_eq!(acceptance["status"], "ACCEPTED_IMPLEMENTATION_VECTOR_SOURCE");
    assert_eq!(acceptance["source_fixture_id"], fixture["fixture_id"]);
    assert_eq!(acceptance["case_count"].as_u64(), Some(44));
    assert_eq!(fixture["cases"].as_array().expect("cases").len(), 44);
}

#[test]
fn rust_candidate_matches_every_accepted_vector() {
    let fixture: Value = serde_json::from_str(&fs::read_to_string(fixture_path()).expect("read fixture"))
        .expect("parse fixture");
    let cases = fixture["cases"].as_array().expect("cases array");

    for case in cases {
        let id = case["id"].as_str().expect("case id");
        if let Some(expected) = case.get("expected_utf8").and_then(Value::as_str) {
            let actual = run_case(case).unwrap_or_else(|error| panic!("{id}: unexpected refusal {error}"));
            assert_eq!(actual, expected.as_bytes(), "{id}: canonical byte mismatch");
        } else {
            let expected = case["expected_refusal"].as_str().expect("expected refusal");
            let error = run_case(case).expect_err("case must refuse before bytes");
            assert_eq!(error.reason(), expected, "{id}: refusal mismatch");
        }
    }
}

#[test]
fn integer_float_and_signed_zero_identity_remain_distinct() {
    assert_eq!(canonical_bytes_v2(&CanonicalValueV2::Integer(1)).unwrap(), b"1");
    assert_eq!(canonical_bytes_v2(&CanonicalValueV2::Float(1.0)).unwrap(), b"1.0");
    assert_eq!(canonical_bytes_v2(&CanonicalValueV2::Float(0.0)).unwrap(), b"0.0");
    assert_eq!(canonical_bytes_v2(&CanonicalValueV2::Float(-0.0)).unwrap(), b"-0.0");
}
