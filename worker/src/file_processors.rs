use std::io;
use std::process::{Command, Output};

pub trait FileProcessor {
    fn process(&self, input_file: &str, output_file: &str) -> io::Result<Output>;
}

pub struct Avif {}
impl FileProcessor for Avif {
    fn process(&self, input_file: &str, output_file: &str) -> io::Result<Output> {
        Command::new("/usr/bin/avifenc")
            .args([
                "-c",
                "aom",
                "-s",
                "4",
                "-j",
                "8",
                "-d",
                "10",
                "-y",
                "444",
                "-q",
                "50",
                "-a",
                "end-usage=q",
                "-a",
                "cq-level=35",
                "-a",
                "tune=iq",
                input_file,
                output_file,
            ])
            .output()
    }
}

pub struct WebP {}
impl FileProcessor for WebP {
    fn process(&self, input_file: &str, output_file: &str) -> io::Result<Output> {
        Command::new("/usr/bin/cwebp")
            .args([
                "/usr/bin/webp",
                "-q",
                "75",
                input_file,
                "-metadata",
                "icc",
                "-o",
                output_file,
            ])
            .output()
    }
}
