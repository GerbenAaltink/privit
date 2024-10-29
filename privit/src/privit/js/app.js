class EventHandler {
    constructor() {
        this.events = {};
        this.eventCount = 0;
        this.suppresEvents = false;
        this.debugEvents = false;
    }
    addEventListener(event, listener) {
        if (!this.events[event]) {
            this.events[event] = { name:name, listeners: [],callCount: 0};
        }
        this.events[event].listeners.push(listener);
    }
    removeEventListener(event, listenerToRemove) {
        if (!this.events[event]) return;
        this.events[event].listeners = this.events[event].listeners.filter(listener => listener !== listenerToRemove);
    }
    fire(event, data) {
        if (!this.events[event]) return [];
        if (this.suppresEvents) return [];
        this.eventCount++;
        const returnValue = this.events[event].listeners.map(listener =>{
            var returnValue = listener(data)
            if(returnValue == undefined)
                return null
            return returnValue
        });
        this.events[event].callCount++;
        if(this.debugEvents){
            console.debug('debugEvent',{event:event, arg:data, callCount: this.events[event].callCount, number:this.eventCount, returnValues:returnValue})
        }
        return returnValue
    }
    suppres(fn) {
        const originallySuppressed = this.suppresEvents
        this.suppresEvents = true 
        fn(this)
        this.suppresEvents = originallySuppressed
        return originallySuppressed
    }
}

class Semaphore {
    constructor(maxConcurrency) {
      this.maxConcurrency = maxConcurrency;
      this.currentConcurrency = 0;
      this.queue = [];
    }
  
    async acquire() {
      if (this.currentConcurrency < this.maxConcurrency) {
        this.currentConcurrency += 1;
        return Promise.resolve();
      }
      
      return new Promise(resolve => {
        this.queue.push(resolve);
      });
    }
  
    release() {
      this.currentConcurrency -= 1;
      if (this.queue.length > 0) {
        this.currentConcurrency += 1;
        const resolve = this.queue.shift();
        resolve();
      }
    }
  
    async use(task) {
      await this.acquire();
      try {
        return await task;
      } finally {
        this.release();
      }
    }
  }
class App extends EventHandler {
    url = null 
    socket = null 
    ws_promises = []
    logedIn = false
    username = null
    semaphore = new Semaphore(1)
    constructor(url='/'){
        super()
        this.url = url
        this.socket = new WebSocket(this.url);
//"ws://localhost:8080/ws"
        const me = this
        this.socket.onopen = (event)=>{
            this.onConnect(event)
        }
        this.socket.onmessage = (event)=>{
            me.onMessage(event)
        }
        
    }
    async login(username,password){
        if(self.loggedIn)
            return true;
        const result = await this.emit('login',{'username':username,'password':password})
        self.loggedIn = result['success']
        if(self.loggedIn){
            self.username = username 
        }
        console.info(result.req_id)
        return self.loggedIn
    }
    async benchmark(user,reader){
        
        if(!user)
            user = 'user'
        if(!reader)
            reader = 'user'

        if(!self.loggedIn)
            await this.login(user,'admin')
        
        let i = 0;
        while(true){
            i++;
            await this.sendMessage(reader,"Hi "+i.toString())
        }
    }
    async sendMessage(reader, message){
        return await app.emit('chat_send',{'reader':reader, 'message':message})
    }
    onEvent(event){
        
    }
    async send(data){
        const me = this 
        return new Promise((resolve,reject)=>{
            me.ws_promises.push(resolve)
            me.socket.send(JSON.stringify(data))
        })
    }
    async emit(event,data){
        data['event'] = event 
        return await this.send(data)
        
    }
    receive(){
        return new Promise((resolve,reject)=>{
            this.ws_promises.push(resolve) 
        });
    }
    onMessage(event){
        const data = JSON.parse(event.data);  // Parse JSON message
        if(this.ws_promises.length){
            let ws_promise =this.ws_promises.shift()
            ws_promise(data) 
            this.fire(data['event'], data);
            
        }else{
            this.fire(data['event'], data);
            
        }
        
    }
    onConnect(event) {
        console.log("connected")
        console.info({app:this})
        this.fire('connected',this)
    }

}

const app = new App(window.location.href.replace(/^http/, 'ws') + 'ws/')
