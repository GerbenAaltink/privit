from aiohttp import web
from aiohttp import hdrs
from aiohttp.web_response import StreamResponse
import aiohttp 
import jinja2
import aiohttp_jinja2
import uuid
import asyncio
import pathlib 
import json 
from privit.ranku_storage import RankuStorage
import json as aioredis
from privit.app import Privit 
from cryptography import fernet
from stogram_client.client import Client as StogramClient
from stogram_client.sync import  Client as StogramSyncClient
import aiohttp_session
import aiohttp_session.redis_storage
from aiohttp_session import setup, new_session, get_session, session_middleware
from aiohttp_session.cookie_storage import EncryptedCookieStorage

class RRedis:

    async def get(self, key):
        print(key)

    async def set(self,key,value):
        print(key, value)


fernet_key = fernet.Fernet.generate_key()
f = fernet.Fernet(fernet_key)


#async def session_middleware(app, handler):
#    response = await handler(handler.request)
#    return response

class Web(web.Application):
    def __init__(self,app,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.sockets = []
        self['app'] = app
        self['tasks'] = []

    async def get_sockets(self):
        for sock in self.sockets:
            yield sock 
    
    async def get_session(self,request):
        return await get_session(request)
        #return await aiohttp_get_session(request)

    async def create_task(self, task):
        self['tasks'].append(task)  

    async def run_services(self):
        while True:
            print("Running services")
            await asyncio.sleep(0.1)
            for task in self['tasks']:
                await task


class WebSocket:

    def __init__(self, connection):
        self.connection = connection 
        self.username = None
        self.password = None
        self.uid = None 
        self.semaphore = asyncio.Semaphore(1)
        self.connected = True 
    async def login(self, username, password):
        self.uid = str(uuid.uuid4())
        self.username = username 
        self.password = password

    async def send(self, data):
        if not self.connected:
            return False 
        try:
            await self.connection.send_str(json.dumps(data,default=str))
        except aiohttp.client_exceptions.ClientConnectionResetError as e:
            self.connected = False 
        return True
    
    async def __aiter__(self):
        try:
            async for msg in self.connection:
                yield msg 
        except RuntimeError:
            
            return


class SessionView(web.View):
    @property
    def session(self):
        return self.request.session

    async def _iter(self):
        if self.request.method not in hdrs.METH_ALL:
            self._raise_allowed_methods()
        #method: Optional[Callable[[], Awaitable[StreamResponse]]]
        method = getattr(self, self.request.method.lower(), None)
        self.method = method 
        if method is None:
            self._raise_allowed_methods()
        self.request.session = await get_session(self.request)
        self.app = self.request.app
        self.request.logged_in = self.request.session.get('username') is not None
        self.logged_in = self.request.logged_in
        self.db = self.app['app'].db
        self.username = self.session.get('username')
        ret = await self.execute()
        return ret 
    
    async def execute(self):
        ret = await self.method()
        assert isinstance(ret, StreamResponse)
        return ret


class AuthenticatedView(SessionView):

    async def execute(self):
        if not self.logged_in:
            return web.json_response(text="Not logged in", status=401)
        return await self.method()


class ChatView(AuthenticatedView):
    
    async def get(self):
        messages = await self.db.chat_message.get(reader=self.username)
        return web.json_response(messages)
class WebHomeView(SessionView):

    @aiohttp_jinja2.template("index.html")
    async def get(self):
        #if not hasattr(self.request,'session'):
        #   self.request.session = await get_session(self.request)
        #    self.request.session['req_id'] = 0
        #session = await get_session(self.request)
        if not self.request.session.get('req_id'):
            self.request.session['req_id'] = 0
        self.request.session['req_id'] += 1
        self.request.session['much_data'] = 'a' * 1024*3
        session = await get_session(self.request)
        
        context = {'message':'hoi {}'.format(self.request.session['req_id']),'session':json.dumps(dict(self.request.session.items()),default=str)}
        return context
    
    
class WebSocketView(SessionView):
    
   
    async def get(self):
        ws = web.WebSocketResponse()
        await ws.prepare(self.request)
        sock = WebSocket(connection=ws)
        self.request.app.sockets.append(sock)
        app = self.request.app['app']
        async for msg in sock.connection:
            if msg.type == web.WSMsgType.TEXT:
                data = json.loads(msg.data)
                if data['event'] == 'chat_send':
                    await app.db.chat_message.create(writer=sock.username,reader=data['reader'],message=data['message'])
                    data['writer'] = sock.username
                    self.request.app.stogram.publish("chat",data)
                
                if data['event'] == 'get_events':
                    events = await app.db.event.get_new()
                    await sock.send({"event": "get_events", "events": events})
                if data['event'] == 'get_messages':
                    messages = await app.db.chat_message.get(reader=sock.username,limit=30)
                    messages.sort(key=lambda x: x['id'], reverse=False)
                    await sock.send({'event':'chat_messages','messages':[message.json for message in messages]})
                if data['event'] == 'login':
                    self.request.session.update(username=data.get('username'))
                    await sock.login(data.get('username'),data.get('password'))
                    await sock.send({"event": "login","req_id":self.session.get('req_id'), "username": data['username'],'success':True})
                

            elif msg.type == web.WSMsgType.ERROR:
                self.request.app.sockets.remove(sock)
                print(f"WebSocket connection closed with exception: {ws.exception()}")
                break

            elif msg.type in [web.WSMsgType.CLOSE,web.WSMsgType.CLOSED,web.WSMsgType.CLOSING]:
                print("WebSocket closed by client gracefully.")
                break

        self.request.app.sockets.remove(sock)       
        #sockets.remove(sock)
        print("WebSocket connection closed")
        return ws


async def init_background_tasks(app):
    app.stogram = StogramSyncClient(host="stogram",port=7001)
    app.stogram.connect()

    privit = app['app']
    
    app['background_task'] = asyncio.create_task(privit.run(web=app))

class PrivetRunner(web.AppRunner):
    def __init__(self, app):
        super().__init__(self.app)
    async def _make_server(self):
        loop = asyncio.get_event_loop()
        self._app._set_loop(loop)
        self._app.on_startup.freeze()
        try:
            await self._app.startup()
        except:
            print("FUUUUCK")
        self._app.freeze()

        return self._app._make_handler(loop=loop, **self._kwargs)


async def start_web(app):
    runner = PrivetRunner(app)
    await runner.setup()  # Set up the runner
    port = 8080
    site = None
    while port < 9000:
        try:
            site = web.TCPSite(runner, "stogram", 8080)  # Specify host and port
            await site.start()  # Start the site
        except:
            port += 1
    print(f"Server is running on {site._host}:{site._port}")  # Access the port


def create_web(db_url):
    app = Web(Privit(url=db_url,verbose=False))
    
    storage = RankuStorage(url=db_url)
    aiohttp_session.setup(app, storage)
    app['provision'] = False
    app.path = pathlib.Path(__file__).parent.resolve()
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(app.path.joinpath('templates')))
    app.router.add_view('/', WebHomeView)
    app.router.add_view('/ws/', WebSocketView)
    app.router.add_view('/chat/', ChatView)
    app.router.add_static('/js/', path=app.path.joinpath('js'), name='static')
    app.on_startup.append(init_background_tasks)
    return app
    
