from utro import AsyncClient
import uuid
import time 
from datetime import datetime
import json 
import asyncio
from stogram_client.client import Client as StogramClient
class DatabaseRecord:

    def __init__(self, qr=None, row=None,**kwargs):
        self._qr = qr
        self.columns = self._qr.columns
        self._db = self._qr.db
        field_number = 0
        self.row = row 
        self.data = {}
        for column in qr.columns:
            if field_number >= len(row):
                break
            self.data[column] = row[field_number]
            self.__dict__[column] = row[field_number]
            field_number+=1
        if kwargs:
            self.data.update(kwargs)
    
        if not self.data.get('uid'):
            self.data['uid'] = self._db.uid()
            self.saved = False 
            self.update_created()
        else:
            self.saved = True 
        
    #def __getattribute__(self, name):
    #    if not object.__getattribute__(self, name):
     #       return object.__getattribute__(self,'data').get(name)
     #   else:
     #       return object.__getattribute__(self, name)
    
    @property
    def initialized(self):
        return self.created_date and True or False

    async def save(self):
        if self.saved:
            columns = []
            values = []
            asterisks = []
            update_part = []
            for key,value in self.__dict__.items():
                columns.append(key)
                asterisks.append("?")
                values.append(value)
                update_part.append("{} = ?".format(key))

            query = "UPDATE {} SET {} WHERE uid = ?".format(self._qr.table_name, ','.join(update_part))
            values.append(self.uid)
            result = await self._db.execute(query,values)
            return result.rows_affected and True or False 
        else:
            query = "INSERT INTO %s (%s) VALUES (%s)" % (self._qr.table_name, ','.join(columns), ','.join(asterisks))   
            result = await self._db.execute(query,values)
            return result.rows_ffected and True or False 
        
    def update_created(self):
        self.data['created_date'] = datetime.now().strftime('%Y-%m-%d')
        self.data['created_time'] = datetime.now().strftime('%H:%M:%S')
        self.data['created'] = self.data['created_date'] + ' ' + self.data['created_time']

    #def __getattribute__(self, name):
    #    if hasattr(self, '__dict__')['data'] and name in object.__getattribute__(self, 'data'):
    #        return object.__getattribute__(self,'data')[name]
    #    else:
    #        return object.__getattribute__(self, name)
        
    def __repr__(self):
        return json.dumps(self.json,indent=1)
        
    @property 
    def json(self):
        return dict(self.data)

    def __getitem__(self, key):
        return self.__dict__.get(key, None)
    
    def __setitem__(self, key, value):
        self.__dict__[key] = value
        self.data[key] = value

class QueryResult:

    def __init__(self, db, result, query, parameters):
        self.query = query 
        self.parameters = parameters 
        self.time_start = None 
        self.time_end = None 
        self.table_name = None
        if not type(result) == dict:
            print(result)
            exit(1)
        self.error = result.get('error', None)
        self.columns = result.get('columns',0)
        if query.lower().find(" from ") > 0:
            start = query[query.lower().find(" from ")+len(" from ") :]
            self.table_name = start[0:start.find(" ")]
        elif query.lower().find(" update ") > 0:
            start = query[query.lower().find(" update ")+len(" update ") :]
            self.table_name = start[0:start.find(" ")]
        self.db = db 
        self.result = result
        self.success = result.get('success')
        self.rows_affected = result.get('rows_affected')
        self.insert_id = result.get('insert_id')
        self.count = result.get('count',0)
        self.rows = [DatabaseRecord(qr=self, row=record) for record in result.get('rows',[])]

    @property
    def json(self):
        return [row.json for row in self.rows]

    def __repr__(self):
        return json.dumps({'query':self.query,'error':self.error,'row_count':len(self.rows),'success':self.success,'insert_id':self.insert_id,'rows_affected':self.rows_affected},indent=1,default=str) 
    @property 
    def duration(self):
        return (self.time_end or 0) - (self.time_start or 0) 
class ChatMessageTable:

    def __init__(self, db):
        self.db = db 

    async def create(self, writer,reader, message):
        uid = self.db.uid()
        await self.db.execute("INSERT INTO chat_message(uid,writer,status,reader,message) VALUES(?,?,?,?,?)",[uid,writer,"new",reader,message])
        await self.db.event.create(user=reader,message="New message from {}".format(writer))
        return uid
    
    async def mark_is_read(self, uid):
        resp = await self.db.execute("UPDATE chat_message SET status = ? WHERE uid = ?",["read",uid])
        return resp.rows_affected
    async def delete(self, uid):
        resp = await self.db.execute("UPDATE chat_message SET status = ? WHERE uid = ?",["deleted",uid])
        return resp.rows_affected
    async def mark_unread(self,uid):
        resp = await self.db.execute("UPDATE chat_message SET status = ? WHERE uid = ?",["new",uid])
        return resp.rows_affected > 0

    async def get(self, uid=None, reader=None,status="new",start=0,limit = 30,sort="DESC"):
        if uid:
            resp = await self.db.execute("SELECT id, uid,writer,status,reader,message FROM chat_message WHERE uid = DESC LIMIT 1",[uid])
        elif reader and status and limit == 1:
            resp = await self.db.execute("SELECT id, uid,writer,status,reader,message FROM chat_message WHERE reader = ? and status = ? ORDER BY id DESC LIMIT ?",[reader,status,limit])
        elif reader and status and limit > 1:
            resp = await self.db.execute("SELECT id, uid,writer,status,reader,message FROM chat_message WHERE reader = ? and status = ? ORDER BY id DESC LIMIT ?",[reader,status,limit])
        elif reader:
            resp = await self.db.execute("SELECT id ,uid,writer,status,reader,message FROM chat_message WHERE reader = ? ORDER BY id  LIMIT ?",[reader,limit])
        else:
            resp = await self.db.execute("SELECT id, uid,writer,status,reader,message FROM chat_message ORDER BY id  LIMIT ?",[reader,limit])
        if not resp.success:
            print(resp.error)
        if not resp.rows:
            return []
        if uid:
            return resp.rows[0]
        return resp.rows

class EventTable:

    def __init__(self, db):
        self.db = db
        

    async def create(self,user, message):
        uid = self.db.uid()
        resp = await self.db.execute("INSERT INTO event (uid,status, user,message) VALUES (?,?,?,?)",[uid,"new",user,message])
        return uid if resp.success else None
    async def mark_is_read(self, uid):
        resp = await self.db.execute("UPDATE event SET status = ? WHERE uid = ?",["read",uid])
        return resp.rows_affected
    async def delete(self, uid):
        resp = await self.db.execute("UPDATE event SET status = ? WHERE uid = ?",["deleted",uid])
        return resp.rows_affected
    async def mark_unread(self,uid):
        resp = await self.db.execute("UPDATE event SET status = ? WHERE uid = ?",["new",uid])
        return resp.rows_affected > 0
    
    async def mark_handled(self,uid):
        await self.db.execute("insert into event_history (app_uid,uid) VALUES (?,?)",[self.db.id,uid])
    async def pop_new(self,id_gt=0):
        resp = None
        async with self.db as transaction:
            #update_resp = await transaction.execute("UPDATE event SET notify_id = ? WHERE notify_id IS NULL and status=? and id > ?",[transaction.id,"new",id_gt])
            #if not update_resp.success:
            #    print(update_resp)    
            
            resp = await transaction.execute("SELECT id, uid,user,message FROM event WHERE id > ? and uid not in (select uid from event_history where app_uid=?)",[id_gt,self.db.id])
            tasks = []
            for row in resp.rows:
                tasks.append(self.mark_handled(row['uid']))
            await asyncio.gather(*tasks)
            #update_resp = await transaction.execute("UPDATE event SET status = ? where notify_id=? and status = ?",[transaction.id, "notified","new"])
            #if not update_resp.success:
            #    print(update_resp)

        return resp.rows

class Database:

    @property
    def verbose(self):
        return self.client.verbose

    @verbose.setter
    def verbose(self, val):
        self.client.verbose = val
    
    async def execute(self, sql, params=None):
        await self.client.connect()
        if self.transaction_id is None:
            self.time_start = time.time()
        resp_start = time.time()
        print("PREPARE: ",sql)
        print("params",params)
        resp = await self.client.execute(sql, params or [])
        print("EXECUTED",resp)
        qr = QueryResult(db=self, result=resp, query=sql, parameters=params or [])
        qr.time_start = resp_start
        self.time_end = time.time()
        qr.time_end = self.time_end
        self.time = self.time_end - self.time_start
        if not qr.success:
            print(qr)
            exit(1)
        self.total_queries_executed +=1
        self.total_query_time += self.time 
        self.avg_query_time = self.total_query_time / self.total_queries_executed
        print("DONE")
        return qr 

    def uid(self):
        return str(uuid.uuid4())

    @property
    def id(self):
        return self.transaction_id and self.transaction_id or self._id

    @id.setter
    def id(self, val):
        self._id = val 

    def __init__(self, url, verbose=False):
        self._id = self.uid()
        self.time_start = None
        self.time_end = None
        self.time = None
        self.total_queries_executed = 0
        self.avg_query_time = 0
        self.total_query_time = 0
        self.url = url 
        self.client =StogramClient(host="127.0.0.1",port=7001)
        self.verbose = verbose
        self.transaction_id = None
        self._transaction_id = 0
        self.event = EventTable(self)
        self.chat_message = ChatMessageTable(self)

    async def delete_schema(self):
        if self.verbose:
            print("Start deleting schema")
        await self.execute("PRAGMA foreign_keys = OFF;")
        indexes = ['idx_event_uid','idx_event_notify_id','idx_event_notify_id_status','idx_chat_message_uid','idx_chat_message_notify_id','idx_chat_message_notify_id_status','idx_chat_message_writer','idx_chat_message_reader','idx_chat_message_reader_status','idx_event_history_uid','idx_event_history_event_uid','idx_event_history_event_uid_app_uid']
        for index in indexes:
            resp = await self.execute("DROP INDEX IF EXISTS {}".format(index))
        resp = await self.execute("drop table if exists session")
        resp = await self.execute("drop table if exists event")
        resp = await self.execute("drop table if exists event_history")
        resp = await self.execute("drop table if exists chat_message")
        await self.execute("PRAGMA foreign_keys = ON;")
        if self.verbose:
            print("Finish deleting schema")
        return resp.success

    async def apply_schema(self):
        if self.verbose:
            print("Start provisioning schema")
        resp = await self.execute("create table event(id integer PRIMARY KEY AUTOINCREMENT, uid text, notify_id text NULL, status text, user text, message text)")
        resp = await self.execute("CREATE INDEX idx_event_uid ON event (uid);")
        resp = await self.execute("CREATE INDEX idx_event_notify_id ON event (notify_id);")
        resp = await self.execute("CREATE INDEX idx_event_notify_id_status ON event (notify_id,status);")
        
        resp = await self.execute("create table chat_message(id integer PRIMARY KEY AUTOINCREMENT, uid text, notify_id text NULL, status text, reader text, writer text, message text)")
        resp = await self.execute("CREATE INDEX idx_chat_message_uid ON chat_message (uid);")
        resp = await self.execute("CREATE INDEX idx_chat_message_notify_id ON chat_message (notify_id);")
        resp = await self.execute("CREATE INDEX idx_chat_message_notify_id_status ON chat_message (notify_id,status);")
        resp = await self.execute("CREATE INDEX idx_chat_message_writer ON chat_message (writer);")
        resp = await self.execute("CREATE INDEX idx_chat_message_reader ON chat_message (reader);")
        resp = await self.execute("CREATE INDEX idx_chat_message_reader_status ON chat_message (reader,status);")
        
        resp = await self.execute("CREATE TABLE event_history (id integer PRIMARY KEY AUTOINCREMENT, uid text,app_uid text, event_uid text NULL)")
        resp = await self.execute("CREATE INDEX idx_event_history_uid ON event_history (uid);")
        resp = await self.execute("CREATE INDEX idx_event_history_event_uid ON event_history (event_uid);")
        resp = await self.execute("CREATE INDEX idx_event_history_event_uid_app_uid ON event_history (event_uid,app_uid);")

        await self.execute("CREATE TABLE session (id integer PRIMARY KEY AUTOINCREMENT, uid text, key text, bytes text, ex text)")
        await self.execute("CREATE INDEX idx_session_uid ON session (uid);")
        await self.execute("CREATE INDEX idx_session_key ON session (key);")
        
        if self.verbose:
            print("Finished provisioning schema")

        return resp.success
    async def provision(self):
        return await self.apply_schema()

    async def __aenter__(self,provision=False):
        self.client.keep_alive=True
        self._transaction_id += 1
        self.transaction_id = "{}-{}".format(self.id,self._transaction_id)
        self.time_start = time.time()
        if self.verbose:
            print("Start session")
        await self.execute("BEGIN TRANSACTION")
        return self 

    async def __aexit__(self, *args, **kwargs):
        if self.verbose:
            print("End session")
        self.client.keep_alive = False
        await self.execute("COMMIT")
        self.transaction_id = None
        
    
