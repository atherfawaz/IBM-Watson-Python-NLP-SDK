import json
from os.path import join, dirname
from ibm_watson import SpeechToTextV1
from ibm_watson.websocket import RecognizeCallback, AudioSource
import threading
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator


textinput = input("Enter your IBM API: ")
authenticator = IAMAuthenticator(textinput)
service = SpeechToTextV1(authenticator=authenticator)
textinput = input("Enter your IBM Cloud Service URL: ")
service.set_service_url(textinput)

models = service.list_models().get_result()
# print(json.dumps(models, indent=2))

model = service.get_model('en-US_BroadbandModel').get_result()
# print(json.dumps(model, indent=2))

#harvard.wav isn't working right now
with open(join(dirname(__file__), '../resources/speech.wav'),
          'rb') as audio_file:
    output = json.dumps(
        service.recognize(
            audio=audio_file,
            content_type='audio/wav').get_result(),
        indent=2)

parsed = json.loads(output)

#write data to json file 
#with open('C:\\Users\\ather\\Desktop\\data.json', 'w') as outfile:
#    json.dump(parsed, outfile)

#print parsed output to show only the transcript
print (parsed['results'][0]['alternatives'][0]['transcript'])

# Example using websockets
class MyRecognizeCallback(RecognizeCallback):
    def __init__(self):
        RecognizeCallback.__init__(self)

    def on_transcription(self, transcript):
        print(transcript)

    def on_connected(self):
        print('Connection was successful')

    def on_error(self, error):
        print('Error received: {}'.format(error))

    def on_inactivity_timeout(self, error):
        print('Inactivity timeout: {}'.format(error))

    def on_listening(self):
        print('Service is listening')

    def on_hypothesis(self, hypothesis):
        print(hypothesis)

    def on_data(self, data):
        print(data)

# Example using threads in a non-blocking way
mycallback = MyRecognizeCallback()
audio_file = open(join(dirname(__file__), '../resources/speech.wav'), 'rb')
audio_source = AudioSource(audio_file)
recognize_thread = threading.Thread(
    target=service.recognize_using_websocket,
    args=(audio_source, "audio/l16; rate=44100", mycallback))
# recognize_thread.start()
