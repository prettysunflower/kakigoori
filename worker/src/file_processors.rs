use std::io;
use std::process::{Command, Output};

pub trait FileProcessor {
    fn process(&self, input_file: &String, output_file: &String) -> io::Result<Output>;
}

pub struct AVIF {}
impl FileProcessor for AVIF {
    fn process(&self, input_file: &String, output_file: &String) -> io::Result<Output> {
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
                input_file.as_str(),
                output_file.as_str(),
            ])
            .output()
    }
}

pub struct WebP {}
impl FileProcessor for WebP {
    fn process(&self, input_file: &String, output_file: &String) -> io::Result<Output> {
        Command::new("/usr/bin/cwebp")
            .args([
                "/usr/bin/webp",
                "-q",
                "75",
                input_file.as_str(),
                "-metadata",
                "icc",
                "-o",
                output_file.as_str(),
            ])
            .output()
    }
}
