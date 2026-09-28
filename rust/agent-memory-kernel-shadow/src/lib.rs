//! Evidence-only Rust shadow of selected deterministic Agent Memory primitives.
//!
//! This crate is not linked into the Agent Memory runtime. It exists to test whether
//! language-neutral behavior can be reproduced in Rust before any FFI or runtime
//! migration is considered.

use std::collections::{BTreeMap, BTreeSet, HashMap};

pub const BM25_K1: f64 = 1.2;
pub const BM25_B: f64 = 0.75;

/// Reproduce `ranking_policy.relevance_tokens`: Unicode lowercase first, then
/// retain contiguous ASCII `[a-z0-9]+` runs.
pub fn relevance_tokens(text: &str) -> Vec<String> {
    let lowered = text.to_lowercase();
    let mut tokens = Vec::new();
    let mut current = String::new();

    for ch in lowered.chars() {
        if ch.is_ascii_lowercase() || ch.is_ascii_digit() {
            current.push(ch);
        } else if !current.is_empty() {
            tokens.push(std::mem::take(&mut current));
        }
    }
    if !current.is_empty() {
        tokens.push(current);
    }
    tokens
}

/// Shadow the Python admitted-set BM25 primitive.
///
/// This function intentionally mirrors the current Python operation order instead
/// of "improving" the formula. Query terms are accumulated in sorted order because
/// #576 established that floating addition order is part of reproducibility.
pub fn admitted_set_bm25(query: &str, texts: &BTreeMap<String, String>) -> BTreeMap<String, f64> {
    let documents: BTreeMap<String, Vec<String>> = texts
        .iter()
        .map(|(reference, text)| (reference.clone(), relevance_tokens(text)))
        .collect();
    let count = documents.len();
    if count == 0 {
        return BTreeMap::new();
    }

    let average = {
        let total: usize = documents.values().map(Vec::len).sum();
        let value = total as f64 / count as f64;
        if value == 0.0 { 1.0 } else { value }
    };

    let mut frequency: HashMap<String, usize> = HashMap::new();
    for tokens in documents.values() {
        let unique: BTreeSet<&str> = tokens.iter().map(String::as_str).collect();
        for token in unique {
            *frequency.entry(token.to_owned()).or_insert(0) += 1;
        }
    }

    let terms: BTreeSet<String> = relevance_tokens(query).into_iter().collect();
    let mut scores = BTreeMap::new();

    for (reference, tokens) in &documents {
        let mut term_counts: HashMap<&str, usize> = HashMap::new();
        for token in tokens {
            *term_counts.entry(token.as_str()).or_insert(0) += 1;
        }

        let mut score = 0.0_f64;
        for term in &terms {
            let tf = *term_counts.get(term.as_str()).unwrap_or(&0);
            if tf == 0 {
                continue;
            }
            let df = *frequency.get(term).unwrap_or(&0) as f64;
            let idf = (1.0 + (count as f64 - df + 0.5) / (df + 0.5)).ln();
            score += idf * tf as f64 * (BM25_K1 + 1.0)
                / (tf as f64
                    + BM25_K1
                        * (1.0 - BM25_B + BM25_B * tokens.len() as f64 / average));
        }
        scores.insert(reference.clone(), score);
    }

    scores
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::path::PathBuf;

    #[derive(Debug)]
    struct Row {
        case: String,
        query: String,
        query_tokens: Vec<String>,
        reference: String,
        text: String,
        expected_tokens: Vec<String>,
        expected_score_bits: u64,
    }

    fn fixture_path() -> PathBuf {
        PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../../reference/fixtures/runtime-kernel/bm25-v1.tsv")
    }

    fn split_tokens(value: &str) -> Vec<String> {
        if value.is_empty() {
            Vec::new()
        } else {
            value.split(',').map(str::to_owned).collect()
        }
    }

    fn rows() -> Vec<Row> {
        let source = fs::read_to_string(fixture_path()).expect("read frozen BM25 fixture");
        source
            .lines()
            .skip(1)
            .filter(|line| !line.trim().is_empty())
            .map(|line| {
                let fields: Vec<&str> = line.split('\t').collect();
                assert_eq!(fields.len(), 7, "malformed fixture row: {line}");
                Row {
                    case: fields[0].to_owned(),
                    query: fields[1].to_owned(),
                    query_tokens: split_tokens(fields[2]),
                    reference: fields[3].to_owned(),
                    text: fields[4].to_owned(),
                    expected_tokens: split_tokens(fields[5]),
                    expected_score_bits: fields[6].parse().expect("u64 score bits"),
                }
            })
            .collect()
    }

    #[test]
    fn frozen_vectors_match_python_oracle_bit_for_bit() {
        let rows = rows();
        let cases: BTreeSet<String> = rows.iter().map(|row| row.case.clone()).collect();
        assert_eq!(cases, BTreeSet::from(["near".into(), "simple".into(), "unicode".into()]));

        for case in cases {
            let selected: Vec<&Row> = rows.iter().filter(|row| row.case == case).collect();
            assert!(!selected.is_empty());
            assert_eq!(relevance_tokens(&selected[0].query), selected[0].query_tokens);

            let texts: BTreeMap<String, String> = selected
                .iter()
                .map(|row| (row.reference.clone(), row.text.clone()))
                .collect();
            let scores = admitted_set_bm25(&selected[0].query, &texts);

            for row in selected {
                assert_eq!(relevance_tokens(&row.text), row.expected_tokens, "{}:{}", case, row.reference);
                let actual = scores.get(&row.reference).expect("score exists").to_bits();
                assert_eq!(actual, row.expected_score_bits, "{}:{}", case, row.reference);
            }
        }
    }

    #[test]
    fn near_fixture_preserves_exact_tie_and_ordering_relation() {
        let rows = rows();
        let selected: Vec<&Row> = rows.iter().filter(|row| row.case == "near").collect();
        let texts: BTreeMap<String, String> = selected
            .iter()
            .map(|row| (row.reference.clone(), row.text.clone()))
            .collect();
        let scores = admitted_set_bm25(&selected[0].query, &texts);
        assert_eq!(scores["a"].to_bits(), scores["b"].to_bits());
        assert!(scores["a"] > scores["c"]);
    }
}
