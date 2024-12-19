import os
import base64
import subprocess
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import sys


# If modifying these SCOPES, delete the file token.json.
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

def clear_attachments_folder(folder_name='attachments'):
    for the_file in os.listdir(folder_name):
        file_path = os.path.join(folder_name, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(e)
def search_emails(service, query, max_results):
    messages = []
    try:
        response = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
        messages.extend(response.get('messages', []))

        while 'nextPageToken' in response and len(messages) < max_results:
            page_token = response['nextPageToken']
            response = service.users().messages().list(userId='me', q=query, maxResults=max_results, pageToken=page_token).execute()
            messages.extend(response.get('messages', []))

        return messages
    except HttpError as error:
        print(f'An error occurred: {error}')
        return messages

def save_email_as_eml(service, message_id, folder_name='attachments'):
    try:
        message = service.users().messages().get(userId='me', id=message_id, format='raw').execute()
        msg_raw = base64.urlsafe_b64decode(message['raw'].encode('ASCII'))
        with open(os.path.join(folder_name, f'{message_id}.eml'), 'wb') as f:
            f.write(msg_raw)
    except HttpError as error:
        print(f'An error occurred: {error}')

def modify_email_labels(service, message_id, label_ids, mark_as_read=True, remove_from_inbox=True):
    try:
        labels_to_add = label_ids
        labels_to_remove = ['UNREAD'] if mark_as_read else []
        if remove_from_inbox:
            labels_to_remove.append('INBOX')
        service.users().messages().modify(userId='me', id=message_id, body={
            'addLabelIds': labels_to_add,
            'removeLabelIds': labels_to_remove
        }).execute()
    except HttpError as error:
        print(f'An error occurred when modifying labels: {error}')

def get_label_id(service, label_name):
    try:
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        for label in labels:
            if label['name'].lower() == label_name.lower():
                return label['id']
        return None
    except HttpError as error:
        print(f'An error occurred when retrieving label ID: {error}')
        return None

def main():
    service = gmail_authenticate()
    os.makedirs('attachments', exist_ok=True)
    clear_attachments_folder()  # Clear the attachments folder at the start
    label_id = get_label_id(service, 'emails-extracted-by-bot')
    if label_id is None:
        print("Label 'emails-extracted-by-bot' not found. Please create it in Gmail.")
        return

    # Read choice and optional count from command line arguments
    if len(sys.argv) < 2:
        print("Please provide the eSIM type number as an argument.")
        return
    choice = sys.argv[1]
    num_emails = int(sys.argv[2]) if len(sys.argv) > 2 else 1  # Default is 1 if not specified

    query_options = {
        '1': ['"Here is your esim!" in:inbox is:unread ', '"Simly" in:inbox is:unread ', '"live chat with us" is:unread in:inbox', 'label:.a-simly-unread is:unread'],
            '2': ['"Your Nomad order" in:all is:unread ', '"Nomad" in:inbox is:unread', '"QR code installation" is:unread in:inbox', 'label:.a-nomad-unread is:unread'],
            '3': ['"Reference number" in:all is:unread', '"Holafly" in:all is:unread'],
            #'4': ['"AirAlo" in:inbox is:unread ', '"Menalink" in:inbox is:unread '],
            '4': ['label:.a-airalo-unread is:unread'],
            '5': ['-airalo -holafly in:inbox is:unread '],
            '6': ['"Mogo eSIM" in:inbox', 'label:.a-mogo-unread in:all'],
            '7': ['in:spam simly is:unread'],
            '8': ['label:emails-extracted-by-bot is:read'],
            #'9': ['label:.a-nomad-unread is:unread "10GB" in:all'],
             '9': ['label:.a-airalo-unread is:unread "menalink"'],
            '10': ['label:.a-unidentified-unread is:unread'],
            '11': ['"simly-Palestine" is:unread in:all'],
            '12': ['"simly-Middle East" is:unread in:all'],
            '13': ['label:.a-airalo-unread is:unread "Discover"'],
            '14': ['label:.a-holafly-unread is:unread "Egypt"'],
            '15': ['label:.a-holafly-unread is:unread "Israel"'],
            '16': ['label:.a-truly-unread is:unread in:all"']
    }

    queries = query_options.get(choice, [])
    found_emails = []

    for query in queries:
        if len(found_emails) < num_emails:
            found_emails.extend(search_emails(service, query, num_emails - len(found_emails)))
        else:
            break

    if len(found_emails) < num_emails:
        print("Not enough emails have been found, proceeding with what we have.")

    for message in found_emails[:num_emails]:
        save_email_as_eml(service, message['id'])
        print(f"Extracted {len(found_emails)} email(s) so far.")
        modify_email_labels(service, message['id'], [label_id])

    print("Emails have been saved, labeled, and removed from the inbox.")
    print("Running 'extractor.py'...")
    subprocess.run(["python3", "extractor.py"])  # Execute another script after processing


if __name__ == '__main__':
    main()
