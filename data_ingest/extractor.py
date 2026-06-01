from abc import ABC, abstractmethod


class Extractor(ABC):
    @abstractmethod
    async def login(self) -> None:
        ...
    
    @abstractmethod
    async def close(self) -> None:
        ...
    
    @classmethod
    async def create(cls, *args, **kwargs):
        instance = cls(*args, **kwargs)

        try:
            await instance.login()
        except Exception as e:
            await instance.close()
            raise e

        return instance

    @abstractmethod
    async def extract(self):
        ...