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

const SHA256_INITIAL: [u32; 8] = [
    0x6a09e667,
    0xbb67ae85,
    0x3c6ef372,
    0xa54ff53a,
    0x510e527f,
    0x9b05688c,
    0x1f83d9ab,
    0x5be0cd19,
];

const SHA256_K: [u32; 64] = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
];

/// Dependency-free SHA-256 used only by the shadow qualification crate.
///
/// Production promotion would use a reviewed cryptographic implementation or a
/// separately qualified primitive. Reimplementing SHA-256 here keeps this first
/// evidence slice independent from third-party dependency resolution.
pub fn sha256_bytes(input: &[u8]) -> [u8; 32] {
    let bit_len = (input.len() as u64).wrapping_mul(8);
    let mut message = input.to_vec();
    message.push(0x80);
    while message.len() % 64 != 56 {
        message.push(0);
    }
    message.extend_from_slice(&bit_len.to_be_bytes());

    let mut state = SHA256_INITIAL;
    for chunk in message.chunks_exact(64) {
        let mut words = [0u32; 64];
        for (index, word) in words.iter_mut().take(16).enumerate() {
            let offset = index * 4;
            *word = u32::from_be_bytes([
                chunk[offset],
                chunk[offset + 1],
                chunk[offset + 2],
                chunk[offset + 3],
            ]);
        }
        for index in 16..64 {
            let s0 = words[index - 15].rotate_right(7)
                ^ words[index - 15].rotate_right(18)
                ^ (words[index - 15] >> 3);
            let s1 = words[index - 2].rotate_right(17)
                ^ words[index - 2].rotate_right(19)
                ^ (words[index - 2] >> 10);
            words[index] = words[index - 16]
                .wrapping_add(s0)
                .wrapping_add(words[index - 7])
                .wrapping_add(s1);
        }

        let mut a = state[0];
        let mut b = state[1];
        let mut c = state[2];
        let mut d = state[3];
        let mut e = state[4];
        let mut f = state[5];
        let mut g = state[6];
        let mut h = state[7];

        for index in 0..64 {
            let big_s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let choose = (e & f) ^ ((!e) & g);
            let temp1 = h
                .wrapping_add(big_s1)
                .wrapping_add(choose)
                .wrapping_add(SHA256_K[index])
                .wrapping_add(words[index]);
            let big_s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let majority = (a & b) ^ (a & c) ^ (b & c);
            let temp2 = big_s0.wrapping_add(majority);

            h = g;
            g = f;
            f = e;
            e = d.wrapping_add(temp1);
            d = c;
            c = b;
            b = a;
            a = temp1.wrapping_add(temp2);
        }

        state[0] = state[0].wrapping_add(a);
        state[1] = state[1].wrapping_add(b);
        state[2] = state[2].wrapping_add(c);
        state[3] = state[3].wrapping_add(d);
        state[4] = state[4].wrapping_add(e);
        state[5] = state[5].wrapping_add(f);
        state[6] = state[6].wrapping_add(g);
        state[7] = state[7].wrapping_add(h);
    }

    let mut digest = [0u8; 32];
    for (index, word) in state.iter().enumerate() {
        digest[index * 4..index * 4 + 4].copy_from_slice(&word.to_be_bytes());
    }
    digest
}

pub fn sha256_hex(text: &str) -> String {
    let digest = sha256_bytes(text.as_bytes());
    let mut output = String::with_capacity(64);
    for byte in digest {
        use std::fmt::Write as _;
        write!(&mut output, "{byte:02x}").expect("writing to String cannot fail");
    }
    output
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

    fn fixture_root() -> PathBuf {
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../reference/fixtures/runtime-kernel")
    }

    fn split_tokens(value: &str) -> Vec<String> {
        if value.is_empty() {
            Vec::new()
        } else {
            value.split(',').map(str::to_owned).collect()
        }
    }

    fn rows() -> Vec<Row> {
        let source = fs::read_to_string(fixture_root().join("bm25-v1.tsv"))
            .expect("read frozen BM25 fixture");
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

    #[test]
    fn frozen_sha256_vectors_match_python_hashlib_exactly() {
        let source = fs::read_to_string(fixture_root().join("sha256-v1.tsv"))
            .expect("read frozen SHA-256 fixture");
        let mut count = 0;
        for line in source.lines().skip(1) {
            if line.is_empty() {
                continue;
            }
            let (input, expected) = line
                .split_once('\t')
                .expect("SHA-256 fixture row must contain one tab");
            assert_eq!(sha256_hex(input), expected, "SHA-256 mismatch for {input:?}");
            count += 1;
        }
        assert_eq!(count, 5);
    }
}
