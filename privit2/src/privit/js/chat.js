

class ChatComponent extends HTMLElement {
    connectedCallback() {
        this.messages.classList.add('chat-container')
        this.input.classList.add('chatbox-input')
        let me = this 
        
    }
    async sendMessage(message){
        
        await app.sendMessage("user",message)
        //this.input.value = ''
    }
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = '/js/chat.css'; // Path to your external CSS file
        this.shadowRoot.append(link);
        this.container = document.createElement('div')
        this.widget = document.createElement('div')
        this.widget.classList.add('chat-widget')
        this.messages = document.createElement('div')
        this.messages.classList.add('chat-container')
        this.widget.appendChild(this.messages)
        this.input = document.createElement('input')
        this.input.classList.add('chatbox-input')
        this.input.setAttribute('placeholder',"Enter message")
        this.widget.appendChild(this.input)
        this.container.appendChild(this.widget)
        let me = this 

        this.shadowRoot.appendChild(this.container)
        app.addEventListener("chat_receive",(data)=>{
            let chatbox = me.messages
            let message = document.createElement("div")
            message.classList.add('message')
            if(data.username == app.username){
                message.classList.add('user-message')
            }else{
            message.classList.add('other-message')
            }
            
            message.innerText = data.writer + ': ' +data.message
                
            chatbox.appendChild(message)
            chatbox.scrollTop = chatbox.scrollHeight;
        })
        app.addEventListener('connected',async (a)=>{
            await app.login('user','user')
            app.emit('get_messages',{}).then((resp)=>{
               
                resp.messages.forEach((msg)=>{
                    let chatbox = me.messages 
                    let message = document.createElement("div")
                    message.classList.add('message')
                    if(resp.username == msg.username){
                        message.classList.add('user-message')
                    }else{
                    message.classList.add('other-message')
                    }
                    message.innerText = msg.writer + ': ' +msg.message
                    chatbox.appendChild(message)
                    chatbox.scrollTop = chatbox.scrollHeight;
                })
            })
        })
        this.input.addEventListener('change',async(e)=>{
            const value = new String(e.target.value)
            await me.sendMessage(value)
            me.input.value = ""
            
        })

    }

}
customElements.define('my-chat', ChatComponent);
