//! Evidence-only Rust candidate for the accepted #609 canonical JSON v2 vectors.
//!
//! This module is not wired into Agent Memory persistence or restart. It exists only
//! to qualify a language-neutral byte contract independently from the Python runtime.

use serde::de::{self, Deserialize, Deserializer, MapAccess, SeqAccess, Visitor};
use std::collections::BTreeSet;
use std::fmt;

#[derive(Clone, Debug, PartialEq)]
pub enum CanonicalValueV2 {
    Null,
    Bool(bool),
    Integer(i128),
    Float(f64),
    String(String),
    Array(Vec<CanonicalValueV2>),
    Object(Vec<(String, CanonicalValueV2)>),
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum CanonicalJsonV2Error {
    NonFiniteBinary64,
    DuplicateObjectKey,
    InvalidUnicodeScalar,
    NonStringObjectKey,
    IntegerOutOfRange,
    InvalidJsonText,
}

impl CanonicalJsonV2Error {
    pub fn reason(&self) -> &'static str {
        match self {
            Self::NonFiniteBinary64 => "non_finite_binary64",
            Self::DuplicateObjectKey => "duplicate_object_key",
            Self::InvalidUnicodeScalar => "invalid_unicode_scalar",
            Self::NonStringObjectKey => "non_string_object_key",
            Self::IntegerOutOfRange => "integer_out_of_range",
            Self::InvalidJsonText => "invalid_json_text",
        }
    }
}

impl fmt::Display for CanonicalJsonV2Error {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.reason())
    }
}

impl std::error::Error for CanonicalJsonV2Error {}

pub fn canonical_bytes_v2(value: &CanonicalValueV2) -> Result<Vec<u8>, CanonicalJsonV2Error> {
    let mut output = String::new();
    write_value(value, &mut output)?;
    Ok(output.into_bytes())
}

fn write_value(value: &CanonicalValueV2, output: &mut String) -> Result<(), CanonicalJsonV2Error> {
    match value {
        CanonicalValueV2::Null => output.push_str("null"),
        CanonicalValueV2::Bool(value) => output.push_str(if *value { "true" } else { "false" }),
        CanonicalValueV2::Integer(value) => output.push_str(&value.to_string()),
        CanonicalValueV2::Float(value) => write_float(*value, output)?,
        CanonicalValueV2::String(value) => write_string(value, output),
        CanonicalValueV2::Array(values) => {
            output.push('[');
            for (index, value) in values.iter().enumerate() {
                if index > 0 {
                    output.push(',');
                }
                write_value(value, output)?;
            }
            output.push(']');
        }
        CanonicalValueV2::Object(values) => {
            let mut seen = BTreeSet::new();
            for (key, _) in values {
                if !seen.insert(key.as_str()) {
                    return Err(CanonicalJsonV2Error::DuplicateObjectKey);
                }
            }
            let mut ordered: Vec<_> = values.iter().collect();
            ordered.sort_by(|left, right| left.0.chars().cmp(right.0.chars()));

            output.push('{');
            for (index, (key, value)) in ordered.into_iter().enumerate() {
                if index > 0 {
                    output.push(',');
                }
                write_string(key, output);
                output.push(':');
                write_value(value, output)?;
            }
            output.push('}');
        }
    }
    Ok(())
}

fn write_float(value: f64, output: &mut String) -> Result<(), CanonicalJsonV2Error> {
    if !value.is_finite() {
        return Err(CanonicalJsonV2Error::NonFiniteBinary64);
    }
    if value == 0.0 {
        output.push_str(if value.is_sign_negative() { "-0.0" } else { "0.0" });
        return Ok(());
    }

    let mut buffer = ryu_js::Buffer::new();
    let token = buffer.format(value);
    output.push_str(token);
    if !token.contains('.') && !token.contains('e') && !token.contains('E') {
        output.push_str(".0");
    }
    Ok(())
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

pub fn string_from_codepoints_v2(codepoints: &[u32]) -> Result<String, CanonicalJsonV2Error> {
    let mut output = String::new();
    for codepoint in codepoints {
        let Some(ch) = char::from_u32(*codepoint) else {
            return Err(CanonicalJsonV2Error::InvalidUnicodeScalar);
        };
        output.push(ch);
    }
    Ok(output)
}

pub fn canonicalize_json_text_v2(text: &str) -> Result<Vec<u8>, CanonicalJsonV2Error> {
    let mut deserializer = serde_json::Deserializer::from_str(text);
    let value = CanonicalValueV2::deserialize(&mut deserializer).map_err(|error| {
        if error.to_string().contains("duplicate_object_key") {
            CanonicalJsonV2Error::DuplicateObjectKey
        } else {
            CanonicalJsonV2Error::InvalidJsonText
        }
    })?;
    deserializer
        .end()
        .map_err(|_| CanonicalJsonV2Error::InvalidJsonText)?;
    canonical_bytes_v2(&value)
}

struct CanonicalValueVisitor;

impl<'de> Visitor<'de> for CanonicalValueVisitor {
    type Value = CanonicalValueV2;

    fn expecting(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("a JSON value supported by the canonical v2 candidate")
    }

    fn visit_unit<E>(self) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(CanonicalValueV2::Null)
    }

    fn visit_none<E>(self) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(CanonicalValueV2::Null)
    }

    fn visit_bool<E>(self, value: bool) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(CanonicalValueV2::Bool(value))
    }

    fn visit_i64<E>(self, value: i64) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(CanonicalValueV2::Integer(value as i128))
    }

    fn visit_u64<E>(self, value: u64) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(CanonicalValueV2::Integer(value as i128))
    }

    fn visit_f64<E>(self, value: f64) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        if !value.is_finite() {
            return Err(E::custom("non_finite_binary64"));
        }
        Ok(CanonicalValueV2::Float(value))
    }

    fn visit_str<E>(self, value: &str) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(CanonicalValueV2::String(value.to_owned()))
    }

    fn visit_string<E>(self, value: String) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(CanonicalValueV2::String(value))
    }

    fn visit_seq<A>(self, mut sequence: A) -> Result<Self::Value, A::Error>
    where
        A: SeqAccess<'de>,
    {
        let mut values = Vec::new();
        while let Some(value) = sequence.next_element::<CanonicalValueV2>()? {
            values.push(value);
        }
        Ok(CanonicalValueV2::Array(values))
    }

    fn visit_map<A>(self, mut map: A) -> Result<Self::Value, A::Error>
    where
        A: MapAccess<'de>,
    {
        let mut entries = Vec::new();
        let mut seen = BTreeSet::new();
        while let Some(key) = map.next_key::<String>()? {
            if !seen.insert(key.clone()) {
                return Err(de::Error::custom("duplicate_object_key"));
            }
            let value = map.next_value::<CanonicalValueV2>()?;
            entries.push((key, value));
        }
        Ok(CanonicalValueV2::Object(entries))
    }
}

impl<'de> Deserialize<'de> for CanonicalValueV2 {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        deserializer.deserialize_any(CanonicalValueVisitor)
    }
}
