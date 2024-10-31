import socket 

def scan(host, port, limit=100):
    max_port = port + limit
    while port < max_port:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            
            print("Trying port:", port)
            if s.connect_ex((host, port)) == 0:
                port+=1
            else:
                print("Chosen port:",port)
                return port  
    return None