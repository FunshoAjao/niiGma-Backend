from abc import ABC, abstractmethod


class PaymentClient(ABC):

    @abstractmethod
    def process_charge(self, **kwargs):

        raise NotImplementedError

    @abstractmethod
    def verify_charge(self, **kwargs):

        raise NotImplementedError
