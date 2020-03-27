#!/usr/bin/env python
#
# Copyright 2016 IBM
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import argparse
import base64
import configparser
import json
import threading
import time
import ssl
import pyaudio
import websocket
from websocket._abnf import ABNF
from ibm_watson import AssistantV2
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from os.path import join, dirname
from ibm_watson import TextToSpeechV1
import wave
from ibm_watson.websocket import SynthesizeCallback
import os
import logging
import click
import google.auth.transport.grpc
import google.auth.transport.requests
import google.oauth2.credentials
from google.assistant.embedded.v1alpha2 import (
    embedded_assistant_pb2,
    embedded_assistant_pb2_grpc
)
import googlesamples.assistant.grpc.assistant_helpers as assistant_helpers
import googlesamples.assistant.grpc.browser_helpers as browser_helpers
from ibm_watson import ToneAnalyzerV3
from ibm_watson.tone_analyzer_v3 import ToneInput

CHUNK = 1024
FORMAT = pyaudio.paInt16
# Even if your default input is multi channel (like a webcam mic),
# it's really important to only record 1 channel, as the STT service
# does not do anything useful with stereo. You get a lot of "hmmm"
# back.
CHANNELS = 1
# Rate is important, nothing works without it. This is a pretty
# standard default. If you have an audio device that requires
# something different, change this.
RATE = 44100
RECORD_SECONDS = 5
FINALS = []
WATSON_INTENTS = {'attendance', 'availability', 'drop_course',
                  'Goodbye', 'Greeting', 'marks', 'mood', 'printfee', 'reg_course'}

REGION_MAP = {
    'us-east': 'gateway-wdc.watsonplatform.net',
    'us-south': 'stream.watsonplatform.net',
    'eu-gb': 'stream.watsonplatform.net',
    'eu-de': 'stream-fra.watsonplatform.net',
    'au-syd': 'gateway-syd.watsonplatform.net',
    'jp-tok': 'gateway-syd.watsonplatform.net',
}

# GLOBALS
TTS_AUTH = None
TTS_SERVICE = None
WATSON_KEY = None
WATSON_AUTH = None
WATSON_ASSISTANT = None
HEADERS = None
USERPASS = None
URL = None
TONE_AUTHENTICATOR = None
TONE_SERVICE = None
PYAUDIO_OBJ = pyaudio.PyAudio()
PYAUDIO_OBJ_INPUT = pyaudio.PyAudio()
# GLOBALS


"""Sample that implements a text client for the Google Assistant Service."""

ASSISTANT_API_ENDPOINT = 'embeddedassistant.googleapis.com'
DEFAULT_GRPC_DEADLINE = 60 * 3 + 5
PLAYING = embedded_assistant_pb2.ScreenOutConfig.PLAYING


class SampleTextAssistant(object):
    """Sample Assistant that supports text based conversations.

    Args:
      language_code: language for the conversation.
      device_model_id: identifier of the device model.
      device_id: identifier of the registered device instance.
      display: enable visual display of assistant response.
      channel: authorized gRPC channel for connection to the
        Google Assistant API.
      deadline_sec: gRPC deadline in seconds for Google Assistant API call.
    """

    def __init__(self, language_code, device_model_id, device_id,
                 display, channel, deadline_sec):
        self.language_code = language_code
        self.device_model_id = device_model_id
        self.device_id = device_id
        self.conversation_state = None
        # Force reset of first conversation.
        self.is_new_conversation = True
        self.display = display
        self.assistant = embedded_assistant_pb2_grpc.EmbeddedAssistantStub(
            channel
        )
        self.deadline = deadline_sec

    def __enter__(self):
        return self

    def __exit__(self, etype, e, traceback):
        if e:
            return False

    def assist(self, text_query):
        """Send a text request to the Assistant and playback the response.
        """
        def iter_assist_requests():
            config = embedded_assistant_pb2.AssistConfig(
                audio_out_config=embedded_assistant_pb2.AudioOutConfig(
                    encoding='LINEAR16',
                    sample_rate_hertz=16000,
                    volume_percentage=0,
                ),
                dialog_state_in=embedded_assistant_pb2.DialogStateIn(
                    language_code=self.language_code,
                    conversation_state=self.conversation_state,
                    is_new_conversation=self.is_new_conversation,
                ),
                device_config=embedded_assistant_pb2.DeviceConfig(
                    device_id=self.device_id,
                    device_model_id=self.device_model_id,
                ),
                text_query=text_query,
            )
            # Continue current conversation with later requests.
            self.is_new_conversation = False
            if self.display:
                config.screen_out_config.screen_mode = PLAYING
            req = embedded_assistant_pb2.AssistRequest(config=config)
            assistant_helpers.log_assist_request_without_audio(req)
            yield req

        text_response = None
        html_response = None
        for resp in self.assistant.Assist(iter_assist_requests(),
                                          self.deadline):
            assistant_helpers.log_assist_response_without_audio(resp)
            if resp.screen_out.data:
                html_response = resp.screen_out.data
            if resp.dialog_state_out.conversation_state:
                conversation_state = resp.dialog_state_out.conversation_state
                self.conversation_state = conversation_state
            if resp.dialog_state_out.supplemental_display_text:
                text_response = resp.dialog_state_out.supplemental_display_text
        return text_response, html_response


def GoogleAPI(api_endpoint, credentials,
              device_model_id, device_id, lang, display, verbose,
              grpc_deadline, transcript):
    # Setup logging.
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)
    # Load OAuth 2.0 credentials.
    try:
        with open(credentials, 'r') as f:
            credentials = google.oauth2.credentials.Credentials(token=None,
                                                                **json.load(f))
            http_request = google.auth.transport.requests.Request()
            credentials.refresh(http_request)
    except Exception as e:
        logging.error('Error loading credentials: %s', e)
        logging.error('Run google-oauthlib-tool to initialize '
                      'new OAuth 2.0 credentials.')
        return

    # Create an authorized gRPC channel.
    grpc_channel = google.auth.transport.grpc.secure_authorized_channel(
        credentials, http_request, api_endpoint)
    logging.info('Connected to %s', api_endpoint)

    with SampleTextAssistant(lang, device_model_id, device_id, display,
                             grpc_channel, grpc_deadline) as assistant:
        # while True:
        #query = click.prompt('')
        click.echo('<you> %s' % transcript)
        response_text, response_html = assistant.assist(text_query=transcript)
        if display and response_html:
            system_browser = browser_helpers.system_browser
            system_browser.display(response_html)
        if response_text:
            click.echo('<@assistant> %s' % response_text)
            return response_text


# sets up the variables
def authentication_function():

    global TTS_AUTH
    global TTS_SERVICE
    global WATSON_KEY
    global WATSON_AUTH
    global WATSON_ASSISTANT
    global HEADERS
    global USERPASS
    global URL
    global TONE_AUTHENTICATOR
    global TONE_SERVICE

    # TTS
    TTS_AUTH = IAMAuthenticator('gV332Uci-w4LVq6fturapl2P88gE50SFtGBG9wjWelYq')
    TTS_SERVICE = TextToSpeechV1(authenticator=TTS_AUTH)
    TTS_SERVICE.set_service_url(
        'https://api.us-south.text-to-speech.watson.cloud.ibm.com/instances/2a38c46e-2eb1-4376-8a09-a7c1713865a4')
    # END TTS

    # STT
    HEADERS = {}
    USERPASS = ":".join(get_auth())
    HEADERS["Authorization"] = "Basic " + base64.b64encode(
        USERPASS.encode()).decode()
    URL = get_url()
    # END STT

    # WATSON
    # put the general watson api key here
    WATSON_AUTH = IAMAuthenticator(
        'AGesgrUJa4L4OVBHpbJgTKfOeCU6kVeVxo2qhIVFqIYS')
    WATSON_ASSISTANT = AssistantV2(
        version='2018-09-20',
        authenticator=WATSON_AUTH)
    WATSON_ASSISTANT.set_service_url(
        'https://api.us-south.assistant.watson.cloud.ibm.com/instances/28f6a127-f399-482b-9b66-5502ad5af6f5')
    # WATSON_ASSISTANT.set_service_url(
    #    'https://api.us-south.assistant.watson.cloud.ibm.com/instances/28f6a127-f399-482b-9b66-5502ad5af6f5')
    # session = WATSON_ASSISTANT.create_session(
    #    "82b5e8f6-5a1d-44a5-930e-a388332db998").get_result()  # put the specific assistant api key
    session = WATSON_ASSISTANT.create_session(
        "9bf7bf36-235e-4089-bf1d-113791da5b43").get_result()  # put the specific assistant api key
    WATSON_KEY = session.get("session_id", "")
    # END WATSON

    # TONE ANALYZER
    TONE_AUTHENTICATOR = IAMAuthenticator(
        'b0DmzKxaFck7YymuFStEYpJPMmt_bbYLPu8fPO9aEend')
    TONE_SERVICE = ToneAnalyzerV3(
        version='2017-09-21',
        authenticator=TONE_AUTHENTICATOR)
    TONE_SERVICE.set_service_url(
        'https://api.us-south.tone-analyzer.watson.cloud.ibm.com/instances/4a4d15eb-5212-447b-8da9-dcad6434130a')
    # TONE ANALUZER

# TTS


def get_speech(transcript, reply):

    # watson api call
    with open("D:\\dev\\IBM_Watson\\Integration\\resources\\test.wav",
              'wb') as audio_file:
        response = TTS_SERVICE.synthesize(
            reply, accept='audio/wav',
            voice="en-US_MichaelV3Voice").get_result()
        audio_file.write(response.content)

    # output via pyaudio
    f = wave.open(
        r"D:\\dev\\IBM_Watson\\Integration\\resources\\test.wav", "rb")

    #p2 = pyaudio.PyAudio()

    stream = PYAUDIO_OBJ.open(format=PYAUDIO_OBJ.get_format_from_width(f.getsampwidth()),
                              channels=f.getnchannels(),
                              rate=f.getframerate(),
                              output=True)
    # read data
    data = f.readframes(CHUNK)

    # play stream
    while data:
        stream.write(data)
        data = f.readframes(CHUNK)

    # stop stream
    stream.stop_stream()
    stream.close()


def get_answer(transcript):
    # put the specific assistant api key
    message = json.dumps(WATSON_ASSISTANT.message(
        "9bf7bf36-235e-4089-bf1d-113791da5b43", WATSON_KEY,
        input={'text': transcript},
        context={
            'metadata': {
                'deployment': 'myDeployment'
            }
        }).get_result())
    # print(json.dumps(message, indent=2))
    #reply = "".join(message.get('output').get('generic').get(0).get('text'))
    parsed_message = json.loads(message)
    reply = parsed_message['output']['generic'][0]['text']
    error = "I didn't understand. You can try rephrasing."
    if (reply != error):
        # if (intent in WATSON_INTENTS):
        # if (transcript.find('Google') == -1 and transcript.find('google') == -1):
        # if (intent != 'Search'):
        print("Your question: ", transcript)
        print("Reply: ", reply)
        #get_speech(transcript, reply)
    else:
        api_key = 'embeddedassistant.googleapis.com'
        credentials = 'C:\\Users\\ather\\AppData\\Roaming\\google-oauthlib-tool\\credentials.json'
        device_id = '6d0bf190-5b07-11ea-b5ca-ecf4bb451b5d'
        device_model_id = 'watson-73b2e-watsongoogle-famt7c'
        lang = 'en-US'
        display = False
        verbose = False
        grpc = 185
        reply = GoogleAPI(api_key, credentials, device_model_id,
                          device_id, lang, display, verbose, grpc, transcript)
        if (reply is None):
            reply = "Sorry, I could not understand that. Could you try rephrasing your question?"
            print("Your question: ", transcript)
            print("Reply: ", reply)
            #get_speech(transcript, reply)
        else:
            #get_speech(transcript, reply)
            dummy = None

    tone = TONE_SERVICE.tone(
        tone_input=reply, content_type="text/plain").get_result()
    if(tone['document_tone']['tones']):
        arr = tone['document_tone']['tones']
        newlist = sorted(arr, key=lambda k: k['score'], reverse=True)
        #{k: v for k, v in sorted(arr.items(), key=lambda item:['score'])}
        tone = newlist[0]['tone_name']
    else:
        tone = "Neutral"
    print('Reply tone: ', tone)


# STT
def read_audio(ws, timeout):
    """Read audio and sent it to the websocket port.

    This uses pyaudio to read from a device in chunks and send these
    over the websocket wire.

    """
    global RATE
    #p = pyaudio.PyAudio()
    # NOTE(sdague): if you don't seem to be getting anything off of
    # this you might need to specify:
    #
    #    input_device_index=N,
    #
    # Where N is an int. You'll need to do a dump of your input
    # devices to figure out which one you want.
    RATE = int(PYAUDIO_OBJ_INPUT.get_default_input_device_info()
               ['defaultSampleRate'])
    stream = PYAUDIO_OBJ_INPUT.open(format=FORMAT,
                                    channels=CHANNELS,
                                    rate=RATE,
                                    input=True,
                                    frames_per_buffer=CHUNK)

    print("* Recording...")
    rec = RECORD_SECONDS or timeout

    for i in range(0, int(RATE / CHUNK * rec)):
        data = stream.read(CHUNK)
        # print("Sending packet... %d" % i)
        # NOTE(sdague): we're sending raw binary in the stream, we
        # need to indicate that otherwise the stream service
        # interprets this as text control messages.
        ws.send(data, ABNF.OPCODE_BINARY)

    # Disconnect the audio stream
    stream.stop_stream()
    stream.close()
    print("* Recording ended.")

    # In order to get a final response from STT we send a stop, this
    # will force a final=True return message.
    data = {"action": "stop"}
    ws.send(json.dumps(data).encode('utf8'))
    # ... which we need to wait for before we shutdown the websocket
    time.sleep(1)
    ws.close()

    # ... and kill the audio device
    # p.terminate()

# SST
def on_message(self, msg):
    """Print whatever messages come in.

    While we are processing any non trivial stream of speech Watson
    will start chunking results into bits of transcripts that it
    considers "final", and start on a new stretch. It's not always
    clear why it does this. However, it means that as we are
    processing text, any time we see a final chunk, we need to save it
    off for later.
    """

    data = json.loads(msg)
    if "results" in data:
        if data["results"][0]["final"]:
            FINALS.clear()
            FINALS.append(data)
        # This prints out the current fragment that we are working on
        print(data['results'][0]['alternatives'][0]['transcript'])

# SST
def on_error(self, error):
    """Print any errors."""
    print(error)

# SST
def on_close(ws):
    """Upon close, print the complete and final transcript."""
    transcript = "".join([x['results'][0]['alternatives'][0]['transcript']
                          for x in FINALS])
    # print("\nHere's the transcript:\n")
    # print(transcript)
    get_answer(transcript)

# SST
def on_open(ws):
    """Triggered as soon a we have an active connection."""
    args = ws.args
    data = {
        "action": "start",
        # this means we get to send it straight raw sampling
        "content-type": "audio/l16;rate=%d" % RATE,
        "continuous": True,
        "interim_results": True,
        # "inactivity_timeout": 5, # in order to use this effectively
        # you need other tests to handle what happens if the socket is
        # closed by the server.
        "word_confidence": True,
        "timestamps": True,
        "max_alternatives": 3
    }

    # Send the initial control message which sets expectations for the
    # binary stream that follows:
    ws.send(json.dumps(data).encode('utf8'))
    # Spin off a dedicated thread where we are going to read and
    # stream out audio.
    threading.Thread(target=read_audio,
                     args=(ws, args.timeout)).start()

# SST
def get_url():
    config = configparser.RawConfigParser()
    config.read('speech.cfg')
    # See
    # https://console.bluemix.net/docs/services/speech-to-text/websockets.html#websockets
    # for details on which endpoints are for each region.
    region = config.get('auth', 'region')
    host = REGION_MAP[region]
    return ("wss://{}/speech-to-text/api/v1/recognize"
            "?model=en-US_BroadbandModel").format(host)

# SST
def get_auth():
    config = configparser.RawConfigParser()
    config.read('speech.cfg')
    apikey = config.get('auth', 'apikey')
    return ("apikey", apikey)

# SST
def parse_args():
    parser = argparse.ArgumentParser(
        description='Transcribe Watson text in real time')
    parser.add_argument('-t', '--timeout', type=int, default=5)
    # parser.add_argument('-d', '--device')
    # parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()
    return args


def main():
    # Connect to websocket interfaces
    #headers = {}
    #userpass = ":".join(get_auth())
    # headers["Authorization"] = "Basic " + base64.b64encode(
    #    userpass.encode()).decode()
    #url = get_url()

    # If you really want to see everything going across the wire,
    # uncomment this. However realize the trace is going to also do
    # things like dump the binary sound packets in text in the
    # console.
    #
    # websocket.enableTrace(True)

    authentication_function()

    # while (True):
    ws = websocket.WebSocketApp(URL,
                                header=HEADERS,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.on_open = on_open
    ws.args = parse_args()
    # This gives control over the WebSocketApp. This is a blocking
    # call, so it won't return until the ws.close() gets called (after
    # 6 seconds in the dedicated thread).
    while(True):
        input("\nPress enter to proceed...")
        ws.run_forever()


if __name__ == "__main__":
    main()
