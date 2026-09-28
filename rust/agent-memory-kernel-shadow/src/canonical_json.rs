//! Dependency-free canonical JSON shadow for the explicitly non-floating domain.
//!
//! This module intentionally cannot represent floating-point values. Persisted Agent
//! Memory state currently includes floats in some integrity surfaces, so numeric
//! canonicalization remains governed separately by #609. This slice qualifies only
//! null, booleans, integers, strings, arrays, and string-keyed objects.

use std::collections::BTreeMap;

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum CanonicalValue {
    Null,
    Bool(bool),
    Integer(i128),
    String(String),
    Array(Vec<CanonicalValue>),
    Object(BTreeMap<String, CanonicalValue>),
}

pub fn canonical_bytes(value: &CanonicalValue) -> Vec<u8> {
    let mut output = String::new();
    write_value(value, &mut output);
    output.into_bytes()
}

fn write_value(value: &CanonicalValue, output: &mut String) {
    match value {
        CanonicalValue::Null => output.push_str("null"),
        CanonicalValue::Bool(value) => output.push_str(if *value { "true" } else { "false" }),
        CanonicalValue::Integer(value) => output.push_str(&value.to_string()),
        CanonicalValue::String(value) => write_string(value, output),
        CanonicalValue::Array(values) => {
            output.push('[');
            for (index, value) in values.iter().enumerate() {
                if index > 0 {
                    output.push(',');
                }
                write_value(value, output);
            }
            output.push(']');
        }
        CanonicalValue::Object(values) => {
            output.push('{');
            for (index, (key, value)) in values.iter().enumerate() {
                if index > 0 {
                    output.push(',');
                }
                write_string(key, output);
                output.push(':');
                write_value(value, output);
            }
            output.push('}');
        }
    }
}

fn write_string(value: &str, output: &mut String) {
    output.push('"');
    for ch in value.chars() {
        match ch {
            '"' => output.push_str("\\\""),
            '\\' => output.push_str("\\\\"),
            '\u{0008}' => output.push_str("\\b"),
            '\u{000C}' => output.push_str("\\f"),
            '\n' => output.push_str("\\n"),
            '\r' => output.push_str("\\r"),
            '\t' => output.push_str("\\t"),
            ch if ch <= '\u{001F}' => {
                use std::fmt::Write as _;
                write!(output, "\\u{:04x}", ch as u32).expect("writing to String cannot fail");
            }
            ch => output.push(ch),
        }
    }
    output.push('"');
}
