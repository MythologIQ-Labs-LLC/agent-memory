// Deterministic #275 code-reality fixture.

pub fn leaf() -> i32 {
    42
}

pub fn middle() -> i32 {
    leaf()
}

pub fn top() -> i32 {
    middle()
}
