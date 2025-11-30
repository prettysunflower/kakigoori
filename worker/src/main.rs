mod file_processors;
mod json_messages;

use crate::json_messages::{TaskRequest, TaskResponse};
use futures_lite::stream::StreamExt;
use lapin::message::Delivery;
use lapin::options::{
    BasicAckOptions, BasicConsumeOptions, BasicPublishOptions, QueueDeclareOptions,
};
use lapin::protocol::constants::REPLY_SUCCESS;
use lapin::types::ShortString;
use lapin::{
    types::FieldTable, BasicProperties, Channel, Connection, ConnectionProperties, Consumer,
};
use std::fs::File;
use std::io::{Read, Write};
use std::{fs, io};

fn generate_consumer_tag(channel: &Channel) -> String {
    format!("ctag{}.{}", channel.id(), uuid::Uuid::new_v4())
}

async fn handle_task(
    delivery: &Delivery,
    process_variant_channel: &Channel,
    task_function: &impl file_processors::FileProcessor,
) -> Result<(), io::Error> {
    let task_request: TaskRequest = serde_json::from_slice(delivery.data.as_slice())?;

    println!("New task! {}", &task_request.variant_id);

    let input_file_path = format!("/tmp/{}_input", &task_request.variant_id);
    let output_file_path = format!("/tmp/{}_output", &task_request.variant_id);

    let mut input_file = File::create(&input_file_path)?;
    input_file.write_all(&task_request.original_file)?;

    let output = task_function.process(&input_file_path, &output_file_path)?;

    if !output.status.success() {
        return Err(io::Error::other(
            format!("process returned error, status {:?}", output.status.code()),
        ));
    }

    println!("Task {} succeeded! Sending...", &task_request.variant_id);

    let mut contents = Vec::new();
    let mut output_file = File::open(&output_file_path)?;
    output_file.read_to_end(&mut contents)?;

    fs::remove_file(&input_file_path)?;
    fs::remove_file(&output_file_path)?;

    let task_response = TaskResponse {
        variant_file: contents,
        variant_id: task_request.variant_id,
    };

    process_variant_channel
        .basic_publish(
            "".into(),
            "process_variant".into(),
            BasicPublishOptions::default(),
            serde_json::to_vec(&task_response)?.as_slice(),
            BasicProperties::default(),
        )
        .await
        .map_err(|_| io::Error::from(io::ErrorKind::Other))?;

    Ok(())
}

async fn handle_queue(
    consumer: &mut Consumer,
    process_variant_channel: Channel,
    task_function: &impl file_processors::FileProcessor,
) -> Result<(), lapin::Error> {
    while let Some(delivery) = consumer.next().await {
        println!("Received message!");

        let delivery = delivery.map_err(|_| io::Error::from(io::ErrorKind::Other))?;

        let task_result = handle_task(&delivery, &process_variant_channel, task_function).await;

        match task_result {
            Ok(_) => (),
            Err(e) => eprintln!("Error handling task: {}", e),
        }

        delivery.ack(BasicAckOptions::default()).await?;
    }

    Ok(())
}

async fn handle_file_type(
    channel: Channel,
    channel_process_variant: Channel,
    queue: &str,
    task_function: impl file_processors::FileProcessor,
) -> Result<Result<(), lapin::Error>, lapin::Error> {
    let queue_declare_options = QueueDeclareOptions {
        durable: true,
        ..Default::default()
    };

    channel
        .queue_declare(queue.into(), queue_declare_options, FieldTable::default())
        .await?;

    channel_process_variant
        .queue_declare(
            "process_variant".into(),
            queue_declare_options,
            FieldTable::default(),
        )
        .await?;

    let mut consumer = channel
        .basic_consume(
            queue.into(),
            generate_consumer_tag(&channel).into(),
            BasicConsumeOptions::default(),
            FieldTable::default(),
        )
        .await?;

    Ok(handle_queue(&mut consumer, channel_process_variant, &task_function).await)
}

async fn connect_rabbit_mq() -> lapin::Result<(Connection, Vec<tokio::task::JoinHandle<Result<Result<(), lapin::Error>, lapin::Error>>>)> {
    let addr =
        std::env::var("RABBITMQ_ADDRESS").unwrap_or_else(|_| "amqp://127.0.0.1:5672/%2f".into());

    let conn = Connection::connect(
        &addr,
        ConnectionProperties::default().with_connection_name("kakigoori-worker".into()),
    )
    .await?;

    let worker_file_types = std::env::var("WORKER_FILE_TYPES")
        .unwrap_or_else(|_| "avif,webp".into())
        .to_lowercase();

    let mut tasks = vec![];
    for file_type in worker_file_types.split(',') {
        match file_type {
            "avif" => {
                tasks.push(tokio::spawn(handle_file_type(
                    conn.create_channel().await?,
                    conn.create_channel().await?,
                    "kakigoori_avif",
                    file_processors::Avif {},
                )));
            }
            "webp" => {
                tasks.push(tokio::spawn(handle_file_type(
                    conn.create_channel().await?,
                    conn.create_channel().await?,
                    "kakigoori_webp",
                    file_processors::WebP {},
                )));
            }
            _ => {}
        }
    }

    Ok((conn, tasks))
}

#[tokio::main]
async fn main() -> io::Result<()> {

    let a = connect_rabbit_mq().await;

    match a {
        Ok((conn, tasks)) => {
            for task in tasks {
                let task_result = task.await?;
                if let Err(e) = task_result {
                    eprintln!("Error handling task: {}", e);
                }
            }

            let conn_close_result = conn.close(REPLY_SUCCESS, ShortString::from("Normal shutdown")).await;
            if let Err(e) = conn_close_result {
                eprintln!("Warning, error closing connection: {}", e);
            }
        }
        Err(error) => {
            eprintln!("Failed to initialize the worker");
            eprintln!("{}", error);
            std::process::exit(1);
        }
    }

    Ok(())
}
