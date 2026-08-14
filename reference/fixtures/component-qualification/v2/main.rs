fn replacement_leaf() -> i32 {
    2
}

fn middle() -> i32 {
    replacement_leaf()
}

fn top() -> i32 {
    middle()
}

fn main() {
    println!("{}", top());
}
