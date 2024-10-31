import asyncio
import jinja2
import aiohttp_jinja2
import aiohttp
import uuid
import argparse
from privit.port_scanner import scan as get_available_port
import logging 
from aiohttp import web
import json
import pathlib
from utro import AsyncClient
from privit.db import Database
from privit.app import Privit
from privit.web import create_web
url = "http://localhost:8888/"


async def run_app(port,verbose=False):
    app = create_web(db_url="http://localhost:8887")
    app['app'].verbose = verbose
    port = get_available_port("127.0.0.1",port)
    event_loop = asyncio.get_event_loop()
    app['app'].provision = port  == 8080
    event_loop.create_task(web._run_app(app,host="0.0.0.0",port=port))

async def run(verbose):
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger("aiohttp.client").setLevel(logging.DEBUG)   # Client logs
        logging.getLogger("aiohttp.server").setLevel(logging.DEBUG)   # Server logs
        logging.getLogger("aiohttp.access").setLevel(logging.DEBUG)

    asyncio.create_task(run_app(8084,verbose=verbose))
    await asyncio.sleep(2)
    asyncio.create_task(run_app(8085,verbose=verbose))
    asyncio.create_task(run_app(8086,verbose=verbose))
    while True:
        await asyncio.sleep(1)

def main():
    
    asyncio.run(run(False))
