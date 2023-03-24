import json
import datetime
import sys
import time
import random
import os
import openai
from slack import post_message_to_slack
import boto3 #Prod
#from dotenv import load_dotenv

def main(event, context):
    #local
    #load_dotenv()
    #OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

    #PROD
    OPENAI_API_KEY = os.environ['OPENAI_API_KEY']

    ## Create Initial Chat Prompt
    INITIAL_PROMPT_STRING = "Generate a medium or hard difficulty practice algorithms interview question \
                            but do not give the solution yet."

    openai.api_key=OPENAI_API_KEY
    model = "gpt-3.5-turbo"
    messages=[
        {"role": "system", "content": "You are a helpful assistant that generates and explains quantitative trading interview questions."},
        {"role": "user", "content": INITIAL_PROMPT_STRING},
    ]

    ## Get production storage parameters that map to previously asked questions
    ssm = boto3.client('ssm')
    NAMES = [f'chat_gpt_q{i}' for i in range(10)]
    ssm_response = ssm.get_parameters(
        Names=NAMES,WithDecryption=False # in order of most recent to least recent
    )
    NEW_PROMPT_STRING = "Generate a new medium or hard difficulty practice algorithms interview question \
                            but do not give the solution yet."

    ## Append previously asked questions to context of current chat prompt                    
    for question in ssm_response['Parameters']:
        if question['Value'] != 'None':
            messages.append({"role": "assistant", "content": question['Value']})
            messages.append({"role": "user", "content": NEW_PROMPT_STRING})

    # Send chat prompt to Chat GPT
    chat_gpt_response = openai.ChatCompletion.create(
    model=model,
    messages=messages
    )

    # Get Chat GPT response and send to Slack
    chat_gpt_response = chat_gpt_response.choices[0].message.content
    post_message_to_slack(chat_gpt_response)

    # Update last questions asked storage parameters
    ten_questions_asked = True
    for q_idx in range(len(NAMES)):
        if ssm_response['Parameters'][q_idx]['Value'] == 'None':
            ten_questions_asked = False
            break

    if ten_questions_asked:
        start_idx = len(NAMES)-1
    else:
        start_idx = q_idx

    for q_idx in range(start_idx, 0, -1):
        
        response = ssm.put_parameter(
            Name=f'chat_gpt_q{q_idx}',
            Value=ssm_response['Parameters'][q_idx-1]['Value'],
            Type='String',
            Overwrite=True
        )

    response = ssm.put_parameter(
        Name=f'chat_gpt_q0',
        Value=chat_gpt_response,
        Type='String',
        Overwrite=True
    )

    
    return {
        'statusCode': 200,
        'body': json.dumps(chat_gpt_response)
    }

    
if __name__ == "__main__":
    main('', '')
