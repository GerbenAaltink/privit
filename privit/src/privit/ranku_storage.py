import json
import uuid
from typing import Any, Callable, Optional

from privit.db import Database
#from utro import AsyncClient
from aiohttp import web

from aiohttp_session import AbstractStorage, Session

class RankuStorage(AbstractStorage):
    """Redis storage"""

    def __init__(
        self,
        url: str,
        *,
        cookie_name: str = "AIOHTTP_SESSION",
        domain: Optional[str] = None,
        max_age: Optional[int] = None,
        path: str = "/",
        secure: Optional[bool] = None,
        httponly: bool = True,
        samesite: Optional[str] = None,
        key_factory: Callable[[], str] = lambda: uuid.uuid4().hex,
        encoder: Callable[[object], str] = json.dumps,
        decoder: Callable[[str], Any] = json.loads,
    ) -> None:
        super().__init__(
            cookie_name=cookie_name,
            domain=domain,
            max_age=max_age,
            path=path,
            secure=secure,
            httponly=httponly,
            samesite=samesite,
            encoder=encoder,
            decoder=decoder,
        )
        self.url = url
        self._key_factory = key_factory
        self._client = Database(self.url)

    async def load_session(self, request: web.Request) -> Session:
        cookie = self.load_cookie(request)
        if cookie is None:
            return Session(None, data=None, new=True, max_age=self.max_age)
        else:
            key = str(cookie)
            
            resp = await self._client.execute("select bytes from session where key=?",[self.cookie_name + "_" + key])
            data_bytes = resp.count and resp.rows[0].bytes or None
            if data_bytes is None:
                return Session(None, data=None, new=True, max_age=self.max_age)
            data_str = data_bytes
            try:
                data = json.loads(data_str)
            except ValueError:
                data = None
            return Session(key, data=data, new=False, max_age=self.max_age)

    async def save_session(
        self, request: web.Request, response: web.StreamResponse, session: Session
    ) -> None:
        key = session.identity
        if key is None:
            key = self._key_factory()
            self.save_cookie(response, key, max_age=session.max_age)
        else:
            if session.empty:
                self.save_cookie(response, "", max_age=session.max_age)
            else:
                key = str(key)
                self.save_cookie(response, key, max_age=session.max_age)

        data_str = json.dumps(self._get_session_data(session))
        resp = await self._client.execute("update session set bytes  = ?, ex= ? where key = ?",[
            data_str,
            session.max_age,
            self.cookie_name + "_" + key
        ])
        if(not resp.rows_affected):
            await self._client.execute("insert into session (key,bytes,ex) values (?,?,?)",[
                self.cookie_name + "_" + key,
                data_str,
                session.max_age
            ])
