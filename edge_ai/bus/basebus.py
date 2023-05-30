from abc import ABC, abstractmethod

class BaseBus(ABC):
    @abstractmethod
    def start(self) -> None:
        ...

    @abstractmethod
    def stop(self) -> None:
        ...

    @abstractmethod
    def read_register(self, register: int) -> int:
        ...

    @abstractmethod
    def write_register(self, register: int, value: int) -> None:
        ...