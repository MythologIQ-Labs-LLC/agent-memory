#[path = "../src/candidate_prefilter.rs"]
mod candidate_prefilter;

use candidate_prefilter::{identity_first_prefilter, CandidateRow};
use std::collections::BTreeMap;
use std::fs;
use std::path::PathBuf;

fn fixture_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../reference/fixtures/runtime-kernel/candidate-prefilter-v1.tsv")
}

#[derive(Debug)]
struct FixtureRow {
    query: String,
    row: CandidateRow,
    expected_score_bits: Option<u64>,
    expected_rank: Option<usize>,
}

#[test]
fn frozen_candidate_prefilter_matches_python_identity_first_semantics() {
    let source = fs::read_to_string(fixture_path()).expect("read candidate prefilter fixture");
    let mut grouped: BTreeMap<String, Vec<FixtureRow>> = BTreeMap::new();

    for line in source.lines().skip(1).filter(|line| !line.is_empty()) {
        let fields: Vec<&str> = line.split('\t').collect();
        assert_eq!(fields.len(), 8, "malformed candidate fixture row: {line}");
        grouped.entry(fields[0].to_owned()).or_default().push(FixtureRow {
            query: fields[1].to_owned(),
            row: CandidateRow {
                uuid: fields[2].to_owned(),
                group_selected: fields[3] == "1",
                identity_eligible: fields[4] == "1",
                fact_text: fields[5].to_owned(),
            },
            expected_score_bits: (!fields[6].is_empty())
                .then(|| fields[6].parse().expect("u64 score bits")),
            expected_rank: (!fields[7].is_empty())
                .then(|| fields[7].parse().expect("usize rank")),
        });
    }

    assert_eq!(
        grouped.keys().map(String::as_str).collect::<Vec<_>>(),
        vec!["domain", "empty", "punctuation", "set-query", "tie"]
    );

    for (case, rows) in grouped {
        let query = &rows[0].query;
        assert!(rows.iter().all(|row| row.query == *query));
        let candidates: Vec<CandidateRow> = rows.iter().map(|row| row.row.clone()).collect();
        let actual = identity_first_prefilter(query, &candidates);

        let mut expected: Vec<(&str, u64, usize)> = rows
            .iter()
            .filter_map(|row| {
                Some((
                    row.row.uuid.as_str(),
                    row.expected_score_bits?,
                    row.expected_rank?,
                ))
            })
            .collect();
        expected.sort_by_key(|item| item.2);

        assert_eq!(
            actual.iter().map(|item| item.0.as_str()).collect::<Vec<_>>(),
            expected.iter().map(|item| item.0).collect::<Vec<_>>(),
            "candidate order mismatch for {case}"
        );
        assert_eq!(
            actual.iter().map(|item| item.1.to_bits()).collect::<Vec<_>>(),
            expected.iter().map(|item| item.1).collect::<Vec<_>>(),
            "candidate score-bit mismatch for {case}"
        );
    }
}
