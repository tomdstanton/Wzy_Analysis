#!/usr/bin/env python3

import urllib.request
import urllib.error
import json
import uuid
from pathlib import Path
from argparse import ArgumentParser

# Constants ------------------------------------------------------------------------------------------------------------
API_BASE_URL = 'http://bioinf.cs.ucl.ac.uk/psipred/api/submission.json'

# Functions ------------------------------------------------------------------------------------------------------------
def parse_args():
    parser = ArgumentParser()
    parser.add_argument('pdbs', type=Path, help='PDB files', nargs='+')
    parser.add_argument('-e', '--email', help='Email address', default="user@example.com")
    return parser.parse_args()


def build_multipart_body(payload, filename, file_bytes):
    """
    Constructs a multipart/form-data body as bytes.
    """
    # Generate a unique boundary string
    boundary = f"----------{uuid.uuid4().hex}".encode('utf-8')

    body = bytearray()

    # Add form fields from the payload dictionary
    for key, value in payload.items():
        body.extend(b'--' + boundary + b'\r\n')
        body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode('utf-8'))
        body.extend(str(value).encode('utf-8') + b'\r\n')

    # Add the file part
    body.extend(b'--' + boundary + b'\r\n')
    body.extend(f'Content-Disposition: form-data; name="input_data"; filename="{filename}"\r\n'.encode('utf-8'))
    body.extend(b'Content-Type: application/octet-stream\r\n\r\n')
    body.extend(file_bytes)
    body.extend(b'\r\n')

    # Add the closing boundary
    body.extend(b'--' + boundary + b'--\r\n')

    return body, boundary


def submit_merizo_search(path: Path, email: str, chain_id: str = 'A', db: str = 'ted'):
    """Submits a single merizosearch job using urllib."""
    submission_name = f"search_{path}_{chain_id}"
    payload = {
        'job': 'merizosearch',
        'submission_name': f"search_{path}_{chain_id}",
        'email': email,
        'merizosearch_db': db,
        'merizosearch_chain': chain_id,
    }

    try:
        # Read the file content as bytes
        file_bytes = path.read_bytes()

        # Build the full request body and get the boundary
        body, boundary = build_multipart_body(payload, path, file_bytes)

        # Prepare the request with appropriate headers
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary.decode("utf-8")}',
            'Content-Length': str(len(body))
        }

        req = urllib.request.Request(API_BASE_URL, data=body, headers=headers, method='POST')

        print(f"Submitting job: {submission_name}...")

        # Send the request and handle the response
        with urllib.request.urlopen(req) as response:
            response_data = response.read()
            response_json = json.loads(response_data.decode('utf-8'))
            print(f"Successfully submitted {submission_name}. Status: {response.status}. Response: {response_json}")

    except FileNotFoundError:
        print(f"Error: File not found at {path}")
    except urllib.error.HTTPError as e:
        print(f"Error submitting job for {path}: HTTP Error {e.code}: {e.reason}")
        print(f"Server response: {e.read().decode('utf-8', 'ignore')}")
    except urllib.error.URLError as e:
        print(f"Error submitting job for {path}: URL Error {e.reason}")


# --- Main script execution ---
if __name__ == "__main__":
    args = parse_args()
    for pdb in args.pdbs:
        if pdb.suffix == '.pdb':
            submit_merizo_search(pdb, args.email)
