#[path = "../candidate_prefilter.rs"]
mod candidate_prefilter;

use agent_memory_kernel_shadow::sha256_bytes;
use candidate_prefilter::{identity_first_prefilter, CandidateRow};
use std::env;
use std::fs;
use std::hint::black_box;
use std::path::PathBuf;
use std::time::Instant;

const CONTRACT: &str = "591_identity_first_prefilter_compute_v1";
const TOPICS: [&str; 10] = [
    "deploy", "memory", "agent", "policy", "tool",
    "project", "user", "current", "history", "graph",
];
const QUERIES: [&str; 8] = [
    "deploy memory project",
    "agent policy current",
    "tool user project 7",
    "history graph item 42",
    "memory memory agent",
    "current project 17",
    "unrelated missing",
    "deploy, graph!",
];

fn build_rows(count: usize) -> Vec<CandidateRow> {
    (0..count)
        .map(|index| {
            let first = TOPICS[index % TOPICS.len()];
            let second = TOPICS[(index * 3 + 1) % TOPICS.len()];
            CandidateRow {
                uuid: format!("ref-{index:06}"),
                group_selected: index % 5 != 0,
                identity_eligible: index % 7 != 0,
                fact_text: format!(
                    "The {first} {second} item {} belongs to project {}.",
                    index % 97,
                    index % 41
                ),
            }
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

fn signature(rows: &[CandidateRow]) -> String {
    let mut material = Vec::new();
    for (query_index, query) in QUERIES.iter().enumerate() {
        for (uuid, score) in identity_first_prefilter(query, rows) {
            material.extend_from_slice(
                format!("{query_index}|{uuid}|{}\n", score.to_bits()).as_bytes(),
            );
        }
    }
    hex(&sha256_bytes(&material))
}

fn percentile_nearest_rank(values: &[f64], percentile: f64) -> f64 {
    if values.is_empty() {
        return 0.0;
    }
    let mut ordered = values.to_vec();
    ordered.sort_by(f64::total_cmp);
    let rank = ((ordered.len() as f64 * percentile).ceil() as usize).max(1);
    ordered[(rank - 1).min(ordered.len() - 1)]
}

fn median(values: &[f64]) -> f64 {
    if values.is_empty() {
        return 0.0;
    }
    let mut ordered = values.to_vec();
    ordered.sort_by(f64::total_cmp);
    let middle = ordered.len() / 2;
    if ordered.len() % 2 == 0 {
        (ordered[middle - 1] + ordered[middle]) / 2.0
    } else {
        ordered[middle]
    }
}

fn parse_args() -> (usize, usize, PathBuf) {
    let mut rows = 20_000usize;
    let mut iterations = 8usize;
    let mut output: Option<PathBuf> = None;
    let args: Vec<String> = env::args().collect();
    let mut index = 1;
    while index < args.len() {
        match args[index].as_str() {
            "--rows" => {
                index += 1;
                rows = args.get(index).expect("--rows value").parse().expect("positive rows");
            }
            "--iterations" => {
                index += 1;
                iterations = args.get(index).expect("--iterations value").parse().expect("positive iterations");
            }
            "--output" => {
                index += 1;
                output = Some(PathBuf::from(args.get(index).expect("--output value")));
            }
            other => panic!("unknown argument: {other}"),
        }
        index += 1;
    }
    assert!(rows > 0 && iterations > 0, "rows and iterations must be positive");
    (rows, iterations, output.expect("--output is required"))
}

fn main() {
    let (row_count, iterations, output) = parse_args();
    let rows = build_rows(row_count);
    let result_signature = signature(&rows);

    let mut checksum = 0u64;
    for query in QUERIES {
        let result = identity_first_prefilter(query, &rows);
        checksum ^= result.len() as u64;
        if let Some((_, score)) = result.first() {
            checksum ^= score.to_bits() & 0xffff;
        }
        black_box(&result);
    }

    let mut samples_ms = Vec::with_capacity(iterations * QUERIES.len());
    let started = Instant::now();
    for _ in 0..iterations {
        for query in QUERIES {
            let query_started = Instant::now();
            let result = identity_first_prefilter(query, &rows);
            samples_ms.push(query_started.elapsed().as_secs_f64() * 1000.0);
            checksum ^= result.len() as u64;
            if let Some((_, score)) = result.first() {
                checksum ^= score.to_bits() & 0xffff;
            }
            black_box(&result);
        }
    }
    let elapsed = started.elapsed();
    let total_ms = elapsed.as_secs_f64() * 1000.0;
    let examined = row_count as f64 * QUERIES.len() as f64 * iterations as f64;
    let throughput = examined / elapsed.as_secs_f64();
    let p50 = median(&samples_ms);
    let p95 = percentile_nearest_rank(&samples_ms, 0.95);

    let payload = format!(
        concat!(
            "{{\n",
            "  \"schema_version\": 1,\n",
            "  \"contract\": \"{}\",\n",
            "  \"implementation\": \"rust\",\n",
            "  \"rows\": {},\n",
            "  \"queries\": {},\n",
            "  \"iterations\": {},\n",
            "  \"sample_count\": {},\n",
            "  \"result_signature_sha256\": \"{}\",\n",
            "  \"total_ms\": {:.6},\n",
            "  \"p50_query_ms\": {:.6},\n",
            "  \"p95_query_ms\": {:.6},\n",
            "  \"projected_rows_examined_per_second\": {:.6},\n",
            "  \"checksum\": {},\n",
            "  \"timing_scope\": \"prefilter_compute_only_rows_prebuilt\",\n",
            "  \"authority_effect\": \"none\"\n",
            "}}\n"
        ),
        CONTRACT,
        row_count,
        QUERIES.len(),
        iterations,
        samples_ms.len(),
        result_signature,
        total_ms,
        p50,
        p95,
        throughput,
        checksum,
    );

    if let Some(parent) = output.parent() {
        fs::create_dir_all(parent).expect("create output directory");
    }
    fs::write(&output, &payload).expect("write Rust benchmark output");
    print!("{payload}");
}
