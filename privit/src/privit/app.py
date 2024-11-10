
from privit.db import Database 
import asyncio 
from privit.stogram import Client as StogramClient
import json
class Privit:

    def __init__(self, url,verbose=False,provision=False):
        self.url = url
        self.db = None
        self.verbose = verbose
        self.provision = provision
        self.stogam = None

    @property
    def verbose(self):
        return self._verbose
    
    @verbose.setter
    def verbose(self,val):
        self._verbose = val
        if self.db:
            self.db.verbose = self._verbose

    async def ping(self):
        while True:
            await asyncio.sleep(5)
            print("Instance:",self.db.id)
            print("Users online:",len(self.web.sockets))
            print("Total execution time:",self.db.total_query_time,"Avg query time:",self.db.avg_query_time,"Total queries:",self.db.total_queries_executed)
            

    async def create_task(self,task):
        self.web.create_task(task)
    
    async def service_chat(self):
        async with StogramClient(port=7001) as client:
            
            print(await client.subscribe('chat'))
            print("SUBSCRIBED");
            async for ab in client:
                event = ab['message']
                tasks = []
                async for sock in self.web.get_sockets():
                    if not sock.username:
                         continue 
                    if sock.username != event['reader']:
                        continue
                    tasks.append(sock.send(event))
                await asyncio.gather(*tasks)
        
    async def run(self,web):
        self.web = web
        self.stogram = StogramClient("privit_publisher")
        await self.stogram.connect(host="stogram",port=7001))
        self.last_event_id = 0
        self.db = Database(url=self.url,verbose=self.verbose)
        if self.provision:
            await self.db.delete_schema()
            await self.db.provision()
            self.provision = False
        asyncio.create_task(self.ping())
        await asyncio.gather(self.service_chat())
        #asyncio.create_task(self.service_chat())
        #await self.sync_events()
        