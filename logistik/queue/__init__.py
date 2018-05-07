from abc import ABC


class IKafkaReader(ABC):
    def run(self):
        raise NotImplementedError()


class IKafkaWriter(ABC):
    def publish(self, message):
        raise NotImplementedError()
