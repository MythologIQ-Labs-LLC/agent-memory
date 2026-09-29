#[path = "../src/canonical_json_v2.rs"]
mod canonical_json_v2;

use agent_memory_kernel_shadow::sha256_bytes;
use canonical_json_v2::{canonical_bytes_v2, CanonicalValueV2};
use serde_json::Value;
use std::collections::BTreeMap;
use std::fs;
use std::path::PathBuf;

const SUBSTRATE_SCHEME: &str = "bmerkle-v2";
const GOVERNANCE_SCHEME: &str = "gsect-v2";
const DIGEST_BUCKETS: usize = 256;
const GOVERNANCE_BUCKETS: usize = 256;
const GOVERNANCE_MAP_SECTIONS: [&str; 5] = [
    "current_fact_by_memory",
    "fact_memory",
    "fact_scope",
    "state_version",
    "tombstones",
];
const GOVERNANCE_LOG_SECTIONS: [&str; 1] = ["events"];

fn fixture_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../reference/fixtures/runtime/canonical-json-v2-commitment-parity-input-v1.json")
}

fn hex(bytes: [u8; 32]) -> String {
    let mut output = String::with_capacity(64);
    for byte in bytes {
        use std::fmt::Write as _;
        write!(&mut output, "{byte:02x}").expect("writing to String cannot fail");
    }
    output
}

fn sha256(data: &[u8]) -> String {
    hex(sha256_bytes(data))
}

fn canonical(value: &CanonicalValueV2) -> Vec<u8> {
    canonical_bytes_v2(value).expect("frozen parity input must be canonicalizable")
}

fn digest(value: &CanonicalValueV2) -> String {
    sha256(&canonical(value))
}

fn from_json(value: &Value) -> CanonicalValueV2 {
    match value {
        Value::Null => CanonicalValueV2::Null,
        Value::Bool(value) => CanonicalValueV2::Bool(*value),
        Value::Number(value) => {
            if let Some(integer) = value.as_i64() {
                CanonicalValueV2::Integer(integer as i128)
            } else if let Some(integer) = value.as_u64() {
                CanonicalValueV2::Integer(integer as i128)
            } else {
                CanonicalValueV2::Float(value.as_f64().expect("finite JSON float"))
            }
        }
        Value::String(value) => CanonicalValueV2::String(value.clone()),
        Value::Array(values) => CanonicalValueV2::Array(values.iter().map(from_json).collect()),
        Value::Object(values) => CanonicalValueV2::Object(
            values
                .iter()
                .map(|(key, value)| (key.clone(), from_json(value)))
                .collect(),
        ),
    }
}

fn object(entries: Vec<(&str, CanonicalValueV2)>) -> CanonicalValueV2 {
    CanonicalValueV2::Object(
        entries
            .into_iter()
            .map(|(key, value)| (key.to_owned(), value))
            .collect(),
    )
}

fn string(value: impl Into<String>) -> CanonicalValueV2 {
    CanonicalValueV2::String(value.into())
}

fn substrate_bucket(table: &str, key: &str) -> usize {
    let material = format!("{table}\0{key}");
    let hash = sha256(material.as_bytes());
    usize::from_str_radix(&hash[..8], 16).expect("bucket prefix") % DIGEST_BUCKETS
}

fn row_hash(table: &str, payload: &Value) -> String {
    digest(&object(vec![
        ("table", string(table)),
        ("row", from_json(payload)),
    ]))
}

fn bucket_digest(values: &[String]) -> String {
    let mut sorted = values.to_vec();
    sorted.sort();
    digest(&CanonicalValueV2::Array(
        sorted.into_iter().map(string).collect(),
    ))
}

fn substrate_root(case: &Value) -> String {
    let substrate = &case["substrate"];
    let mut buckets: Vec<Vec<String>> = vec![Vec::new(); DIGEST_BUCKETS];
    for (table, key_name) in [
        ("episodes", "uuid"),
        ("facts", "uuid"),
        ("typed_relations", "relation_id"),
    ] {
        let source_name = if table == "typed_relations" { "relations" } else { table };
        for payload in substrate[source_name].as_array().expect("row array") {
            let key = payload[key_name].as_str().expect("row key");
            let bucket = substrate_bucket(table, key);
            buckets[bucket].push(row_hash(table, payload));
        }
    }
    let bucket_values = CanonicalValueV2::Array(
        buckets
            .iter()
            .map(|rows| string(bucket_digest(rows)))
            .collect(),
    );
    let material = object(vec![
        ("scheme", string(SUBSTRATE_SCHEME)),
        ("schema_version", from_json(&substrate["schema_version"])),
        (
            "relation_schema_version",
            from_json(&substrate["relation_schema_version"]),
        ),
        ("id_counter", from_json(&substrate["id_counter"])),
        ("buckets", bucket_values),
    ]);
    format!("{SUBSTRATE_SCHEME}:{}", digest(&material))
}

fn governance_bucket(section: &str, key: &str) -> usize {
    let material = format!("{section}\0{key}");
    let hash = sha256(material.as_bytes());
    usize::from_str_radix(&hash[..8], 16).expect("bucket prefix") % GOVERNANCE_BUCKETS
}

fn text_hash(parts: Vec<String>) -> String {
    digest(&CanonicalValueV2::Array(parts.into_iter().map(string).collect()))
}

fn governance_entry_hash(section: &str, key: &str, value_json: &str) -> String {
    text_hash(vec![
        "entry".into(),
        section.into(),
        key.into(),
        value_json.into(),
    ])
}

fn governance_chain(section: &str, seq: usize, previous: &str, value_json: &str) -> String {
    text_hash(vec![
        "log".into(),
        section.into(),
        seq.to_string(),
        previous.into(),
        sha256(value_json.as_bytes()),
    ])
}

fn map_root(section: &str, bucket_digests: Vec<String>) -> String {
    digest(&object(vec![
        ("section", string(section)),
        (
            "buckets",
            CanonicalValueV2::Array(bucket_digests.into_iter().map(string).collect()),
        ),
    ]))
}

fn governance_root(case: &Value) -> String {
    let governance = &case["governance"];
    let maps = governance["maps"].as_object().expect("governance maps");
    let logs = governance["logs"].as_object().expect("governance logs");

    let mut map_roots: Vec<(String, CanonicalValueV2)> = Vec::new();
    for section in GOVERNANCE_MAP_SECTIONS {
        let values = maps[section].as_object().expect("map section");
        let mut buckets: Vec<Vec<String>> = vec![Vec::new(); GOVERNANCE_BUCKETS];
        for (key, value) in values {
            let value_json = String::from_utf8(canonical(&from_json(value))).expect("canonical UTF-8");
            let bucket = governance_bucket(section, key);
            buckets[bucket].push(governance_entry_hash(section, key, &value_json));
        }
        let digests: Vec<String> = buckets.iter().map(|rows| bucket_digest(rows)).collect();
        map_roots.push((section.to_owned(), string(map_root(section, digests))));
    }

    let mut log_roots: Vec<(String, CanonicalValueV2)> = Vec::new();
    for section in GOVERNANCE_LOG_SECTIONS {
        let values = logs[section].as_array().expect("log section");
        let mut count = 0usize;
        let mut head = String::new();
        for value in values {
            count += 1;
            let value_json = String::from_utf8(canonical(&from_json(value))).expect("canonical UTF-8");
            head = governance_chain(section, count, &head, &value_json);
        }
        log_roots.push((
            section.to_owned(),
            object(vec![
                ("count", CanonicalValueV2::Integer(count as i128)),
                ("head", string(head)),
            ]),
        ));
    }

    let residual_digest = digest(&from_json(&governance["residual"]));
    let material = CanonicalValueV2::Object(vec![
        ("scheme".into(), string(GOVERNANCE_SCHEME)),
        ("maps".into(), CanonicalValueV2::Object(map_roots)),
        ("logs".into(), CanonicalValueV2::Object(log_roots)),
        ("residual".into(), string(residual_digest)),
    ]);
    format!("{GOVERNANCE_SCHEME}:{}", digest(&material))
}

fn logical_state_digest(case: &Value) -> String {
    let governance = object(vec![
        ("maps", from_json(&case["governance"]["maps"])),
        ("logs", from_json(&case["governance"]["logs"])),
        ("residual", from_json(&case["governance"]["residual"])),
    ]);
    let material = object(vec![
        ("substrate", from_json(&case["substrate"])),
        ("governance", governance),
    ]);
    format!("sha256:{}", digest(&material))
}

fn main() {
    let payload: Value = serde_json::from_str(&fs::read_to_string(fixture_path()).expect("read parity fixture"))
        .expect("parse parity fixture");
    assert_eq!(
        payload["status"],
        Value::String("FROZEN_INPUT_ONLY_NO_EXPECTED_ROOTS".into())
    );

    let mut output: BTreeMap<String, BTreeMap<String, String>> = BTreeMap::new();
    for case in payload["cases"].as_array().expect("cases") {
        let mut result = BTreeMap::new();
        result.insert("governance_commitment".into(), governance_root(case));
        result.insert("logical_state_digest".into(), logical_state_digest(case));
        result.insert("substrate_commitment".into(), substrate_root(case));
        output.insert(case["id"].as_str().expect("case id").to_owned(), result);
    }
    println!("{}", serde_json::to_string(&output).expect("serialize parity output"));
}
