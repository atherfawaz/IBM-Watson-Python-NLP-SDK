import socket
import threading
from threading import Condition
import json
import wave

state_update = False
blender_state = 0
nlp_state = None
Condition1 = Condition()
Condition2 = Condition()


class nlpThreadlisten(threading.Thread):
    def __init__(self, clientAddress, clientsocket):
        threading.Thread.__init__(self)
        self.csocket = clientsocket
        self.caddress = clientAddress
        print("New connection added: ", clientAddress)

    def run(self):
        print("Connection from : ", self.caddress)
        msg = 'transferred'
        while True:

            # instruction from client
            client_message = self.csocket.recv(2048)
            client_message = client_message.decode()
            if client_message == 'DISCONNECT':
                break
            elif client_message == 'SEND_JSON':
                # server receive
                data = self.csocket.recv(2048)
                print("data from client", data)
                state = self.csocket.recv(2048)
                print("state from client", state)
                self.csocket.send(bytes(msg, 'UTF-8'))
                self.csocket.send(bytes(msg, 'UTF-8'))
                print('here')
            elif client_message == 'SEND_WAV':
                # server receives wav file
                with open('rcvd_file.wav', 'wb') as f:
                    while True:
                        l = self.csocket.recv(2048);
                        if l == bytes('end', 'UTF-8'): break
                        f.write(l)
                    print("Wav file received")
                    f.close()

            elif client_message == 'RECEIVE':
                # loading data from file and reading state
                state = 'THINKING'
                data = json.load(open('data.json'))
                # sending state and json data
                self.csocket.send(bytes(json.dumps(data), 'UTF-8'))
                self.csocket.sendall(bytes(state, 'UTF-8'))
                # receiving confirmation that data has been sent
                in_data = self.csocket.recv(2048)
                print("From Client ", self.caddress, " : ", in_data.decode())

            elif client_message == "Update_State":
                # send updated state
                client_message = self.csocket.recv(2048)

                # send state to the client
                global blender_state
                global Condition1
                Condition1.acquire()
                try:
                    blender_state = int.from_bytes(client_message, byteorder='big')
                    Condition1.notify()
                finally:
                    Condition1.release()

        print("Client at ", self.caddress, " disconnected...")


class nlpThreadsend(threading.Thread):
    def __init__(self, clientAddress, clientsocket):
        threading.Thread.__init__(self)
        self.csocket = clientsocket
        self.caddress = clientAddress
        print("New connection added: ", clientAddress)

    def run(self):
        print("Connection from : ", self.caddress)

        global Condition2
        global nlp_state
        while True:
            with Condition2:
                Condition2.wait()
                self.csocket.sendall(nlp_state)
                state_update = False


class blenderThreadsend(threading.Thread):
    def __init__(self, clientAddress, clientsocket):
        threading.Thread.__init__(self)
        self.csocket = clientsocket
        self.caddress = clientAddress
        print("New connection added: ", clientAddress)

    def run(self):
        print("Connection from : ", self.caddress)

        global state_update
        global blender_state
        global Condition1
        while True:
            with Condition1:
                Condition1.wait()
                self.csocket.sendall((int(blender_state).to_bytes(2, byteorder='big')))
                state_update = False


class blenderThreadlisten(threading.Thread):
    def __init__(self, clientAddress, clientsocket):
        threading.Thread.__init__(self)
        self.csocket = clientsocket
        self.caddress = clientAddress
        print("New connection added: ", clientAddress)

    def run(self):
        client_message = self.csocket.recv(1024)

        # send state to the client
        global nlp_state
        global Condition2
        while True:
            client_message = self.csocket.recv(1024)
            Condition2.acquire()
            try:
                nlp_state = client_message
                Condition2.notify()
            finally:
                Condition2.release()


def init_server():
    LOCALHOST = "127.0.0.1"
    PORT = 10005
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((LOCALHOST, PORT))
    print("Server started")
    print("Waiting for client request..")
    # creating threads for every client
    server.listen(1)
    clientsock, clientAddress = server.accept()
    blender = blenderThreadsend(clientAddress, clientsock)
    blender2 = blenderThreadlisten(clientAddress, clientsock)
    blender.start()
    blender2.start()
    print("Waiting for client request..")
    server.listen(1)
    clientsock, clientAddress = server.accept()
    nlp = nlpThreadlisten(clientAddress, clientsock)
    nlp2 = nlpThreadsend(clientAddress, clientsock)
    nlp.start()
    nlp2.start()
    server.listen(1)
    print('there')


if __name__ == '__main__':
    init_server()
