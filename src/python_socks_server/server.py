from abc import ABC, abstractmethod


class SocksServer(ABC):
    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass
