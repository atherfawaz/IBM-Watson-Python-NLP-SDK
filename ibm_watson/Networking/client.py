import json
import os
import socket
from time import time

wait = False

out_data = ''
posture_input = ''
time_input = None
flag_gesture_input = False  # use this flag to identify if there was an input from CV in past duration


def send_data(jsonfilename, client, clientinput):
    # sending input to server (ie DISCONNECT)

    client.sendall(bytes(clientinput, 'UTF-8'))

    print("Sending JSON")
    # loading data from file
    data = json.load(open(jsonfilename))

    # sending state and json data
    client.send(bytes(json.dumps(data), 'UTF-8'))

    # receiving confirmation that data has been sent
    print('JSON Sent')
    in_data = client.recv(1025)
    print("From Server :", in_data.decode())


def send_wav_data(wavfilename, client, clientinput):
    # sending input to server (ie DISCONNECT)
    print("Sending .wav")
    client.sendall(bytes(clientinput, 'UTF-8'))
    size = os.path.getsize(wavfilename)
    print(size)
    file_size_b = size.to_bytes(4, 'big')
    sent = 0
    counter = 0
    # loading and sending from wav file
    client.sendall(file_size_b)
    # client.sendall(int(size).to_bytes(2, byteorder='big'))
    with open(wavfilename, 'rb') as f:
        for l in f:
            sent += client.send(l)
            counter += 1
        print(counter)

        f.close()
    client.sendall(bytes('end', 'UTF-8'))  # this is the termination bytes
    print(".wav Sent")


in_data = client.recv(1024)
print("From Server :", in_data.decode())


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


def send_message(client, input_msg):
    client.sendall(bytes(input_msg, 'UTF-8'))


def flag_check(event):
    global time_input
    global flag_gesture_input
    duration = 1.0
    while True:
        event_is_set = event.wait()
        flag_gesture_input = True
        while flag_gesture_input:
            current_time = time()
            if current_time - time_input > duration:
                flag_gesture_input = False
        event.clear()


def main_job(e):
    while True:
        event_is_set = e.wait()
        out_data = input("Input your choice: ")
        out_data = out_data.upper()
        print(out_data)
        if out_data == 'SEND_JSON':
            send_data('data.json', client, out_data, 'IDLE')

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
