from confluent_kafka import Producer
import socket 
import json
from config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC
conf={
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'client.id': socket.gethostname()
}
producer=Producer(conf)
def delivery_report(err, msg):
    if err is not None:
        print(f"Delivery failed for message{msg.key()}: {err}")
    else:
        print(f"Message delivered to {msg.topic()} partition [{msg.partition()}] at offset {msg.offset()}")

def send_click_event(event_dict):
    producer.produce(KAFKA_TOPIC, json.dumps(event_dict), callback=delivery_report)
    producer.poll(0)