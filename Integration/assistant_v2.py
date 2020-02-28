import json
from ibm_watson import AssistantV2
import ssl
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

authenticator = IAMAuthenticator(
    'yjsnqyHlLV6Hre2gSL9LqtdAaU9hhRBm7Y_f3k8QTS0v')
assistant = AssistantV2(
    version='2018-09-20',
    authenticator=authenticator)
assistant.set_service_url(
    'https://api.us-south.assistant.watson.cloud.ibm.com/instances/20b1e02e-12ff-4ab0-87e6-469aa5868021')

#########################
# Sessions
#########################

session = assistant.create_session(
    "478bd1ae-7f5a-40b5-b40c-98e1d28ffd99").get_result()
print(json.dumps(session, indent=2))

key = session.get("session_id", "")

#assistant.delete_session(
#    "478bd1ae-7f5a-40b5-b40c-98e1d28ffd99", session).get_result()

#########################
# Message
#########################

message = assistant.message(
    "478bd1ae-7f5a-40b5-b40c-98e1d28ffd99",key,
    input={'text': 'Which university do you go to?'},
    context={
        'metadata': {
            'deployment': 'myDeployment'
        }
    }).get_result()
print(json.dumps(message, indent=2))
