from privit.db import Database 


import asyncio 


async def main():
    db = Database("http://localhost:7001")
    await db.delete_schema()
    await db.provision()



asyncio.run(main())


