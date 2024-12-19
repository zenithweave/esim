import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import time

# Define SCOPES
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def gmail_authenticate():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server()
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

# Define your queries and corresponding labels
queries_labels = {
    '.a-nomad-unread': ['"Your Nomad order" in:inbox is:unread -label:.a-nomad-unread', '"Nomad" in:inbox is:unread -label:.a-nomad-unread'],
    '.a-simly-unread': ['"Here is your esim!" in:inbox is:unread -label:.a-simly-unread', '"Simly" in:inbox is:unread -label:.a-simly-unread',
                         '"live chat with us" is:unread in:inbox -label:.a-simly-unread'],
    '.a-airaloTine-unread': ['"Tine Mobile" in:inbox is:unread -label:.a-airaloTine-unread'],
    '.a-airalo-unread': ['"AirAlo" in:inbox is:unread -label:.a-airalo-unread -label:.a-airaloTine-unread', '"Menalink" in:inbox is:unread -label:.a-airalo-unread'],
    '.a-mogo-unread': ['"Mogo eSIM" in:inbox is:unread -label:.a-mogo-unread'],
    '.a-holafly-unread': ['"Reference number" in:inbox is:unread -label:.a-holafly-unread', '"Holafly" in:inbox is:unread -label:.a-holafly-unread', '"unlimited" in:inbox is:unread -label:.a-holafly-unread'],
    '.a-numero-unread': ['"numero" in:inbox is:unread -label:.a-numero-unread'],
    '.a-truly-unread': ['"truly" in:inbox is:unread -label:.a-truly-unread', '"truely" in:inbox is:unread -label:.a-truly-unread'],
    '.a-unidentified-unread': ['-label:.a-unidentified-unread -label:.a-holafly-unread -label:.a-nomad-unread -label:.a-simly-unread -label:.a-airalo-unread -label:.a-truly-unread -label:.a-mogo-unread is:unread in:inbox ']

}

def add_labels(service, user_id, msg_id, label_ids):
    try:
        message = service.users().messages().modify(userId=user_id, id=msg_id, body={'addLabelIds': label_ids}).execute()
        # print(f"Label added to message {msg_id}")
    except HttpError as error:
        print(f'An error occurred: {error}')

def get_label_id(service, user_id, label_name):
    labels_response = service.users().labels().list(userId=user_id).execute()
    labels = labels_response.get('labels', [])
    for label in labels:
        if label['name'] == label_name:
            return label['id']
    # Create label if it doesn't exist
    new_label = {'name': label_name}
    created_label = service.users().labels().create(userId=user_id, body=new_label).execute()
    return created_label['id']

def main():
    while True:
        try:
            service = gmail_authenticate()
            user_id = 'me'
            total_emails_processed = 0

            # Process each query and apply labels
            try:
                for label_name, queries in queries_labels.items():
                    print(f"Starting processing for label: {label_name}")
                    label_id = get_label_id(service, user_id, label_name)
                    total_processed = 0

                    for query in queries:
                        print(f"Searching emails with query: '{query}'")
                        response = service.users().messages().list(userId=user_id, q=query).execute()

                        if 'messages' in response:
                            messages = response['messages']

                            while 'nextPageToken' in response:
                                page_token = response['nextPageToken']
                                response = service.users().messages().list(userId=user_id, q=query, pageToken=page_token).execute()
                                messages.extend(response['messages'])

                            # Process emails in batches
                            for i in range(0, len(messages), 100):
                                batch = messages[i:i+100]
                                for message in batch:
                                    add_labels(service, user_id, message['id'], [label_id])
                                total_processed += len(batch)

                            print(f"Finished processing {len(messages)} messages for query: '{query}'. Total processed for label '{label_name}': {total_processed}")

                        else:
                            print(f"No messages found for query: '{query}'")

                    print(f"Finished processing for label: {label_name}. Total emails processed: {total_processed}")
            except HttpError as error:
                print(f'An error occurred: {error}')

            print(f"Total emails processed in this cycle: {total_emails_processed}")

            print("Waiting for 3 minutes before the next cycle...")
            time.sleep(180)  # Wait for 3 minutes (180 seconds)
        except Exception as e:
            # print(f"An error occurred: {e}")
            # print("Restarting the script after a short pause...")
            time.sleep(120)


if __name__ == '__main__':
    main()
