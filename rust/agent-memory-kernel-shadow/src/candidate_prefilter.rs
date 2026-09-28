//! Evidence-only shadow of the #591 identity-first lexical candidate prefilter.
//!
//! This module is candidate generation only. Identity eligibility remains a caller-
//! supplied minimisation decision, and any promoted runtime must still perform full
//! governed eligibility/admission after materialization.

use std::collections::BTreeSet;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CandidateRow {
    pub uuid: String,
    pub group_selected: bool,
    pub identity_eligible: bool,
    pub fact_text: String,
}

pub fn candidate_terms(text: &str) -> BTreeSet<String> {
    text.split_whitespace()
        .map(|token| token.trim_matches(|ch| matches!(ch, '.' | ',' | ';' | ':' | '!' | '?')))
        .filter(|token| !token.is_empty())
        .map(str::to_lowercase)
        .collect()
}

pub fn identity_first_prefilter(query: &str, rows: &[CandidateRow]) -> Vec<(String, f64)> {
    let terms = candidate_terms(query);
    let denominator = terms.len().max(1) as f64;
    let mut survivors = Vec::new();

    for row in rows {
        if !row.group_selected || !row.identity_eligible {
            continue;
        }
        let fact_terms = candidate_terms(&row.fact_text);
        let overlap = terms.intersection(&fact_terms).count();
        if overlap == 0 {
            continue;
        }
        survivors.push((row.uuid.clone(), overlap as f64 / denominator));
    }

    survivors.sort_by(|left, right| {
        right
            .1
            .total_cmp(&left.1)
            .then_with(|| left.0.cmp(&right.0))
    });
    survivors
}
