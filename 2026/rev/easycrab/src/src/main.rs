use std::io::{self, Write};
use std::process;

static ENC: [u8; 37] = [
    69, 78, 87, 126, 113, 56, 115, 55, 122, 130, 105, 126, 64, 115, 65, 110, 114, 134, 102, 114,
    68, 119, 124, 108, 139, 92, 123, 143, 77, 140, 108, 126, 134, 85, 83, 111, 161,
];

fn main() {
    print!("Enter the flag: ");
    io::stdout().flush().unwrap();
    let mut input = String::new();
    io::stdin()
        .read_line(&mut input)
        .expect("Failed to read line");

    let trimmed_input = input.trim();
    let input_bytes = trimmed_input.as_bytes();

    if input_bytes.len() != ENC.len() {
        println!("WRONG!!!!");
        process::exit(1);
    }

    for (idx, byte) in input_bytes.iter().enumerate() {
        if byte + (idx as u8) != ENC[idx] {
            println!("WRONG!!!!");
            process::exit(1);
        }
    }

    println!("CORRECT!!!!");
}
