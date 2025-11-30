    use serde::{Deserialize, Serialize};

    mod base64 {
        use base64::{Engine as _, engine::general_purpose::STANDARD};
        use serde::{Deserialize, Serialize};
        use serde::{Deserializer, Serializer};

        pub fn serialize<S: Serializer>(v: &Vec<u8>, s: S) -> Result<S::Ok, S::Error> {
            let base64 = STANDARD.encode(v);
            String::serialize(&base64, s)
        }

        pub fn deserialize<'de, D: Deserializer<'de>>(d: D) -> Result<Vec<u8>, D::Error> {
            let base64 = String::deserialize(d)?;
            STANDARD
                .decode(base64.as_bytes())
                .map_err(serde::de::Error::custom)
        }
    }

    #[derive(Deserialize)]
    pub struct TaskRequest {
        #[serde(with = "base64")]
        pub original_file: Vec<u8>,
        pub variant_id: String,
    }

    #[derive(Serialize)]
    pub struct TaskResponse {
        #[serde(with = "base64")]
        pub variant_file: Vec<u8>,
        pub variant_id: String,
    }
