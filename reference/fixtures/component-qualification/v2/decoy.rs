fn decoy_leaf() -> i32 {
    9
}

fn middle() -> i32 {
    decoy_leaf()
}

fn main() {
    println!("{}", middle());
}
