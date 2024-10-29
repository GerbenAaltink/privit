
from privit.db import Database 
import asyncio 

class Privit:

    def __init__(self, url,verbose=False,provision=False):
        self.url = url
        self.db = None
        self.verbose = verbose
        self.provision = provision

    @property
    def verbose(self):
        return self._verbose
    
    @verbose.setter
    def verbose(self,val):
        self._verbose = val
        if self.db:
            self.db.verbose = self._verbose


    
    async def sync_events(self):
        while True:
            await asyncio.sleep(0.1)
            unread_events = await self.db.event.pop_new(id_gt=self.last_event_id)
            tasks = []
            for event in unread_events:
                self.last_event_id = event.id
                for sock in self.web['sockets']:
                    if not sock.username:
                        break 
                    if not sock.username == event.user:
                        continue
                    
                    messages = await self.db.chat_message.get(reader=sock.username,status="new",limit=1)
                    for message in messages:
                        message['event'] = 'chat_receive'
                        tasks.append(sock.send(message.json))
                        message = None
            await asyncio.gather(*tasks)
            
    async def ping(self):
        while True:
            await asyncio.sleep(5)
            print("Instance:",self.db.id)
            print("Users online:",len(self.web['sockets']))
            print("Total execution time:",self.db.total_query_time,"Avg query time:",self.db.avg_query_time,"Total queries:",self.db.total_queries_executed)
            print("ping")

    async def create_task(self,task):
        self.web.create_task(task)

    async def run(self,web):
        self.web = web
        self.last_event_id = 0
        self.db = Database(url=self.url,verbose=self.verbose)
        if self.provision:
            await self.db.delete_schema()
            await self.db.provision()
            self.provision = False
        asyncio.create_task(self.ping())
        await self.sync_events()
        