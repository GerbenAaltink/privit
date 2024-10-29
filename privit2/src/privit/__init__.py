import aiohttp 
import socket
import json
import asyncio
import time
import sys
import traceback
import requests


   
        

class AsyncClient:

    @property
    def keep_alive(self):
        return self.headers.get("Connection") == "keep-alive"
    @keep_alive.setter
    def keep_alive(self, value):
        if value:
            self.headers["Connection"] = "keep-alive"
        else:
            self.headers.pop("Connection", None)

    def __init__(self, url,keep_alive=False,verbose=False):
        self.timeout = aiohttp.ClientTimeout(total=10 * 60, sock_connect=10*60)
        self.url = url
        self.headers = {}
        self.keep_alive = keep_alive
        self.connector = None 
        self.client = None
        self.verbose = verbose

    async def connect(self):

        self.connector = aiohttp.TCPConnector() #keepalive_timeout=60
        self.client = aiohttp.ClientSession(headers=self.headers,connector=self.connector) # timeout=self.timeout 
        
    async def close(self):
        if(self.client):
            await self.client.close()
            self.connector = None 
            self.client = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def execute(self, query, params=None):
        if query.startswith(".verbose"):
            self.verbose = not self.verbose 
            return "verbose is now " + (self.verbose and "enabled" or "disabled")
        
        payload = dict(query=query,params=params or [])
        if(self.verbose):
            print("sending",payload)
        response = await self.client.post(self.url, json=payload)
        if self.verbose:
            print("received",await response.text())
        try:
            return await response.json()
        except json.decoder.JSONDecodeError:
            return await response.text()
    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

class Client:

    def __init__(self, url,keep_alive=False,verbose=False):
        self.url = url
        self.host,self.port = url.strip("http://").strip("https://").strip("/").split(":")
        self.port = int(self.port)
        self.host = self.host
        self.keep_alive = keep_alive
        self.verbose = verbose

    def execute(self, query, params=None):
        async def _execute(context, query, params=None):
            async with AsyncClient(context.url,verbose=context.verbose,keep_alive=context.keep_alive) as client:
                result = await client.execute(query, params)
                context.verbose = client.verbose 
                context.keep_alive = client.keep_alive
                return result
        context = self
        return asyncio.run(_execute(context,query, params))

    def __enter__(self):
        return self
    def __exit__(self, type, value, traceback):
        pass
