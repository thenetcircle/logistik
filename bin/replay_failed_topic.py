import yaml
import os
import psycopg2
import sys
from kafka import KafkaConsumer, TopicPartition, KafkaProducer, OffsetAndMetadata

lk_env = os.getenv('LK_ENVIRONMENT') or sys.argv[1]
if lk_env is None:
    raise RuntimeError('need environment variable LK_ENVIRONMENT')


def load_secrets_file(config: dict) -> dict:
    from string import Template
    import ast

    secrets_path = f'secrets/{lk_env}.yaml'

    # first substitute environment variables, which holds precedence over the yaml config (if it exists)
    template = Template(str(config))
    template = template.safe_substitute(os.environ)

    if os.path.isfile(secrets_path):
        try:
            secrets = yaml.safe_load(open(secrets_path))
        except Exception as e:
            raise RuntimeError("Failed to open secrets configuration {0}: {1}".format(secrets_path, str(e)))
        template = Template(template)
        template = template.safe_substitute(secrets)

    return ast.literal_eval(template)


def create_connection(config):
    dbname = config['database']['name']
    dbhost = config['database']['host']
    dbport = config['database']['port']
    dbuser = config['database']['username']
    dbpass = config['database']['password']

    try:
        return psycopg2.connect("dbname='%s' user='%s' host='%s' port='%s' password='%s'" % (
            dbname, dbuser, dbhost, dbport, dbpass)
        )
    except:
        raise RuntimeError('could not connect to db')


def get_topics(conn):
    cur = conn.cursor()
    cur.execute("""select distinct event, failed_topic from handler_conf_entity where failed_topic is not null""")
    results = cur.fetchall()
    conn.commit()

    return results


def get_failed_events(config, from_topic, to_topic):
    consumer = KafkaConsumer(
        bootstrap_servers=config['kafka']['hosts'],
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        auto_commit_interval_ms=1000,
        group_id=to_topic
    )

    n_partitions = len(consumer.partitions_for_topic(from_topic))
    events_to_publish = list()
    commit_options = dict()

    for partition_idx in range(n_partitions):
        partition = TopicPartition(from_topic, partition_idx)
        consumer.assign([partition])

        # we'll start reading from this position
        from_offset = consumer.position(partition)

        # obtain the last offset value
        consumer.seek_to_end(partition)
        to_offset = consumer.position(partition)

        print(f'partition_idx: {partition_idx}, from_offset: {from_offset}, to_offset: {to_offset}')
        # no new events since last replay
        if from_offset >= to_offset:
            continue

        consumer.seek(partition, from_offset)

        for message in consumer:
            event = str(message.value, 'utf-8')
            events_to_publish.append(event)
            if message.offset >= to_offset - 1:
                """
                from kafka-python team on github (https://github.com/dpkp/kafka-python/issues/645):
                    "the metadata is really just an opaque string. You can also pass None. 
                    Nothing uses metadata internally, it is there as a way for you to s
                    tore application-specific data if needed." 
                """
                commit_options[partition] = OffsetAndMetadata(message.offset + 1, None)
                break

    consumer.commit(commit_options)
    return events_to_publish


def publish(config, events_to_publish, to_topic):
    producer = KafkaProducer(
        value_serializer=lambda v: v.encode('utf-8'),
        bootstrap_servers=config['kafka']['hosts']
    )

    for event in events_to_publish:
        producer.send(to_topic, event)


def read_config():
    config = yaml.safe_load(open('config.yaml'))
    return load_secrets_file(config)


def replay_failed_events():
    config_dict = read_config()
    topics = get_topics(create_connection(config_dict))

    for to_topic, failed_topic in topics:
        events_to_publish = get_failed_events(config=config_dict, from_topic=failed_topic, to_topic=to_topic)

        print(f'found {len(events_to_publish)} events to publish from {failed_topic} to {to_topic}')
        publish(config=config_dict, events_to_publish=events_to_publish, to_topic=to_topic)


if __name__ == '__main__':
    replay_failed_events()
