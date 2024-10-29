import socket 

def scan(host, port, limit=10):
    max_port = port + limit
    while port < max_port:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex((host, port)) == 0:
                port+=1
            else:
                return port  
    return None