import json
import socket
import threading
from threading import Condition
from threading import Thread

blender_state = None
nlp_state = None
Cv_blender = [None] * 2
Cv_nlp = None
Condition1 = Condition()
Condition2 = Condition()
Condition3 = Condition()
Condition4 = Condition()
blender_clinet = None
blender_client_CV = None
NLP_client = None


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
            print('nlp')
            print(client_message)
            if client_message == 'DISCONNECT':
                break
            elif client_message.upper() == 'SEND_JSON':
                # server receive
                data = self.csocket.recv(2048)
                blender_clinet.sendall(bytes('SEND_JSON', 'UTF-8'))
                blender_clinet.sendall(data)
                print("data from client", data)
                # state = self.csocket.recv(2048)
                # print("state from client", state)
                self.csocket.sendall(bytes(msg, 'UTF-8'))
                print('here')
            elif client_message.upper() == 'SEND_WAV':
                # server receives wav file
                blender_clinet.sendall(bytes('SEND_WAV', 'UTF-8'))
                b_len = self.csocket.recv(1043)
                length = int.from_bytes(b_len, byteorder='big')
                print(length)
                self.csocket.sendall(bytes('hello there', 'UTF-8'))
                self.csocket.sendall(bytes('hello there', 'UTF-8'))
                blender_clinet.sendall(b_len)
                print(blender_clinet.recv(1550).decode())
                # gets stuck after this

                # time.sleep(100)

                counter = 0
                with open('server_rcvd_file.wav', 'wb') as f:
                    while counter <= length:
                        l = self.csocket.recv(2048);
                        counter += len(l)
                        # counter += l.size()
                        # print(counter)
                        blender_clinet.send(l)  # forwards to blender client
                        f.write(l)
                        # this one works
                        # if l == bytes('end', 'UTF-8'): break
                print(counter)
                f.close()
                self.csocket.sendall(bytes(msg, 'UTF-8'))
                response = blender_clinet.recv(1550)
                print(response.decode())
                print("Wav file received")



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
                print('nlp')
                print(client_message)
                # send state to the client
                global blender_state
                global Condition1
                Condition1.acquire()
                try:
                    blender_state = client_message
                    Condition1.notify()
                finally:
                    Condition1.release()

        print("Client at ", self.caddress, " disconnected...")


class Threadsend(threading.Thread):
    def __init__(self, clientAddress, clientsocket, Condition, send_message, purpose):
        threading.Thread.__init__(self)
        self.csocket = clientsocket
        self.caddress = clientAddress
        self.Condition = Condition
        self.message = send_message
        self.purpose = purpose
        print("New connection added: ", clientAddress)

    def run(self):
        print("Connection from : ", self.caddress)

        global state_update
        global blender_state
        while True:
            with self.Condition:
                self.Condition.wait()
                self.csocket.sendall(bytes(self.purpose, 'UTF-8'))
                print(self.purpose)
                print(self.message)
                self.csocket.sendall(self.message)


class nlpThreadsend(threading.Thread):
    def __init__(self, clientAddress, clientsocket):
        threading.Thread.__init__(self)
        self.csocket = clientsocket
        self.caddress = clientAddress
        print("New connection added: ", clientAddress)

    global nlp_state

    def run(self):
        print("Connection from : ", self.caddress)

        global state_update
        global nlp_state
        global Condition2
        while True:
            with Condition2:
                Condition2.wait()
                self.csocket.sendall(bytes('Update_state', 'UTF-8'))
                self.csocket.sendall(nlp_state)


class blenderThreadsend(threading.Thread):
    def __init__(self, clientAddress, clientsocket):
        threading.Thread.__init__(self)
        self.csocket = clientsocket
        self.caddress = clientAddress
        print("New connection added: ", clientAddress)

    global blender_state

    def run(self):
        print("Connection from : ", self.caddress)
        global Condition1
        global state_update
        global blender_state
        while True:
            with Condition1:
                Condition1.wait()
                self.csocket.sendall(bytes('Update_state', 'UTF-8'))
                print('blender')
                print(blender_state)
                self.csocket.sendall(blender_state)


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
                print('hello')
                # print(nlp_state)
                if nlp_state == b'start':
                    Condition2.notify()
            finally:
                Condition2.release()


class CVThreadlisten(threading.Thread):
    def __init__(self, clientAddress, clientsocket):
        threading.Thread.__init__(self)
        self.csocket = clientsocket
        self.caddress = clientAddress
        print("New connection added: ", clientAddress)

    def run(self):
        # send state to the client
        global Cv_blender
        global Cv_nlp
        global Condition3
        global Condition4
        global NLP_client
        global blender_client_CV
        while True:
            # client_message = self.csocket.recv(4096)
            # client_message = client_message.decode()
            # print(client_message)
            # if client_message.upper() == 'GLOBAL':
            #     self.csocket.sendall(bytes('start', 'UTF-8'))
            x = self.csocket.recv(4096)  # get x coord from CV
            self.csocket.sendall(bytes('got x', 'UTF-8'))
            blender_client_CV.sendall(x)
            blender_client_CV.recv(2048).decode()
            y = self.csocket.recv(4086)  # get y coord from CV
            self.csocket.sendall(bytes('got y', 'UTF-8'))
            blender_client_CV.sendall(y)
            blender_client_CV.recv(2048).decode()

        # elif client_message.upper() == 'INPUT':
        #     ui = self.csocket.recv(4096)
        #     NLP_client.sendall(bytes('CV_input', 'UTF-8'))
        #     NLP_client.sendall(ui)
        # else:
        #     self.csocket.sendall(bytes("wrong input", 'UTF-8'))


def send_nlp_cv(client):
    global NLP_client
    global blender_clinet
    while True:
        msg = client.recv(2056)
        print(msg)
        if msg == bytes('nlp', 'UTF-8'):
            client.sendall(bytes('got it', 'UTF-8'))
            msg = client.recv(2056)
            NLP_client.sendall(bytes('cv_input', 'UTF-8'))
            NLP_client.sendall(msg)
        elif msg == bytes('cv', 'UTF-8'):
            client.sendall(bytes('got it', 'UTF-8'))
            msg = client.recv(2056)
            blender_clinet.sendall(bytes('update_state', 'UTF-8'))
            blender_clinet.sendall(msg)


def initialize_threads(thread_type, clientAddress, clientsock):
    rcv = 'Recived'
    global Condition1
    global Condition2
    global Condition3
    global Condition4
    global nlp_state
    global blender_state
    global Cv_blender
    global Cv_nlp
    global blender_clinet
    global NLP_client
    global blender_client_CV

    thread_type = thread_type.decode()

    if thread_type.upper() == 'NLP':
        nlp = nlpThreadlisten(clientAddress, clientsock)
        nlp2 = nlpThreadsend(clientAddress, clientsock)
        # nlp3 = Threadsend(clientAddress, clientsock, Condition3, Cv_nlp, 'CV_Input')

        nlp.start()
        nlp2.start()
        # nlp3.start()
        NLP_client = clientsock

    elif thread_type.upper() == 'BLENDER':

        blender = blenderThreadsend(clientAddress, clientsock)
        blender2 = blenderThreadlisten(clientAddress, clientsock)
        # blender3 = Threadsend(clientAddress, clientsock, Condition4, Cv_blender, 'CV_Input')
        blender.start()
        blender2.start()
        # blender3.start()
        blender_clinet = clientsock

    elif thread_type.upper() == 'CV':
        CV = CVThreadlisten(clientAddress, clientsock)
        CV.start()
    elif thread_type.upper() == 'CV_NLP':
        print('nlp x cv')
        nlp_cv = threading.Thread(target=send_nlp_cv, args=(clientsock,))
        nlp_cv.start()
        dothis = 0
    else:
        return 0
    return 1


def listen_special(server):
    global blender_client_CV
    server.listen(1)
    clientsock, clientAddress = server.accept()
    blender_client_CV = clientsock
    print('oh yeah baby connected')


def init_server():
    LOCALHOST = '127.0.0.1'
    PORT = 10005
    PORT_blender_cv = 10010
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((LOCALHOST, PORT))
    server_cv_blender = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_cv_blender.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_cv_blender.bind((LOCALHOST, PORT_blender_cv))
    print("Server started")
    # creating threads for every client
    special_listen = Thread(target=listen_special, args=(server_cv_blender,))
    special_listen.start()

    while True:

        print("Waiting for client request..")
        server.listen(1)
        clientsock, clientAddress = server.accept()
        if initialize_threads(clientsock.recv(1024), clientAddress, clientsock):
            clientsock.sendall(bytes('Connection Established', 'UTF-8'))
        else:
            clientsock.sendall(bytes('invalid Connection string', 'UTF-8'))


if __name__ == '__main__':
    init_server()
