import json
import socket
from threading import Thread, Event

wait = False

out_data = ''


def send_data(jsonfilename, client, clientinput, state="LISTENING"):
    # sending input to server (ie DISCONNECT)
    client.sendall(bytes(clientinput, 'UTF-8'))

    # loading data from file
    data = json.load(open(jsonfilename))

    # sending state and json data
    client.send(bytes(json.dumps(data), 'UTF-8'))
    client.sendall(bytes(state, 'UTF-8'))

    # receiving confirmation that data has been sent
    print('here')
    in_data = client.recv(1024)
    print("From Server :", in_data.decode())


def send_wav_data(wav_file, client, clientinput):
    # sending input to server (ie DISCONNECT)
    client.sendall(bytes(clientinput, 'UTF-8'))

    # loading and sending from wav file
    with open(wav_file, 'rb') as f:
        for l in f:
            client.sendall(l)
        f.close()
        client.sendall(bytes('end', 'UTF-8'))


def client_receive(client, clientinput):
    # sending client input
    client.sendall(bytes(clientinput, 'UTF-8'))
    msg = 'received'
    # receiving data and state from server
    data = client.recv(1024)
    print("data from client", data)
    state = client.recv(1043)
    print("state from client", state)
    # sending message to server that transmission was successful
    client.send(bytes(msg, 'UTF-8'))
    return data, state


def send_message(input_msg):
    client.sendall(bytes(input_msg, 'UTF-8'))


def main_job(e):
    while True:
        event_is_set = e.wait()
        out_data = input("Input your choice: ")
        out_data = out_data.upper()
        print(out_data)
        if out_data == 'SEND_JSON':
            send_data('data.json', client, out_data, 'IDLE')
            print("here")
        elif out_data == 'SEND_WAV':
            send_wav_data('output.wav', client, out_data)
            print("wav file data sent")
        elif out_data == 'DISCONNECT':
            send_message('DISCONNECT')
            close_NLP(client)
            break
        elif out_data == 'UPDATE_STATE':
            inp = input("Enter state")
            # send state to the client
            send_message('Update_State')
            client.sendall((int(inp).to_bytes(2, byteorder='big')))
        elif out_data == 'RECEIVE':
            data, state = client_receive(client, out_data)
        e.clear()


def init_NLP():
    # establishing connection
    SERVER = "196.194.237.64"
    PORT = 10005
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((SERVER, PORT))
    return client


def close_NLP(client):
    client.close()



