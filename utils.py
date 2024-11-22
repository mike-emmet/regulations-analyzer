import requests
import random
import string
from bs4 import BeautifulSoup
import re


def clean_text(html_content):
    # Parse the HTML content
    soup = BeautifulSoup(html_content, "html.parser")

    # Extract only textual data
    text = soup.get_text()
    cleaned_text = re.sub(r'[^\x00-\x7F]+', ' ', text)  # Remove non-ASCII characters like '�'
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)  # Replace multiple spaces with a single space
    cleaned_text = cleaned_text.strip()  # Remove leading/trailing spaces

    # Print the cleaned text
    return cleaned_text


def generate_short_filename(extension=""):
    # Generate a 10-character string
    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    return f"{random_string}.{extension}" if extension else random_string


def download_pdf(url):
    try:
        # Send a GET request to the URL
        response = requests.get(url, stream=True, timeout=30)

        # Check for successful response
        if response.status_code == 200 and "text/html" in response.headers.get("Content-Type", ""):
            # Extract filename from the URL
            file_name = generate_short_filename("htm")
            file_name = f"downloads/{file_name}"

            # Write the content to a file
            with open(file_name, "wb") as pdf_file:
                for chunk in response.iter_content(chunk_size=8192):
                    pdf_file.write(chunk)

            print(f"PDF downloaded successfully: {file_name}")
            return file_name
        else:
            print(f"Failed to download PDF. Status Code: {response.status_code}")
    except Exception as e:
        print(f"An error occurred: {e}")
    return None
