
class A_Extractor(Extractor):
    def __init__(self):
        self.session: Optioinal[aiohttp.ClientSession] = None
        ...

    @classmethod
    async def create(cls):
        extractor = cls()

        try:
            await extractor.login()
        except Exception as e:
            await extractor.close()
            raise e
        
        return extractor
    
    async def login(self):
        ...

    async def close(self) -> None:
        if self.session is not None:
            await self.session.close()
            self.session = None

    async def extract(self) -> list[]