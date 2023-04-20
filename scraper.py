import requests
from bs4 import BeautifulSoup
import smtplib
import time
from difflib import ndiff
import logging
import configparser

logging.basicConfig(level=logging.INFO)

config = configparser.ConfigParser()
config.read('assets/config.ini')

SENDER_EMAIL = config['email']['sender_email']
SENDER_PASSWORD = config['email']['sender_password']
RECIPIENT_EMAIL = config['email']['recipient_email']
SMTP_SERVER = config['email']['smtp_server']
SCRAPE_FREQUENCY = config['scrape']['frequency']

def on_start():
    logging.info("Scraper running!")
    logging.info(f"Sender email: {SENDER_EMAIL}")
    logging.info(f"Recipient email: {RECIPIENT_EMAIL}")
    logging.info(f"SMTP server: {SMTP_SERVER}")

def get_website_files(url, path=''):
    response = requests.get(url + path)
    soup = BeautifulSoup(response.text, 'html.parser')
    files = []
    for link in soup.find_all('a'):
        href = link.get('href')
        if href.startswith('/'):
            files.extend(get_website_files(url, href))
        else:
            files.append(path + href)
    return files

WEBSITE_LINKS = [link for link in config['websites'].values()]

WEBSITE_CONTENTS = {}

def get_website_contents(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.text

def get_file_contents(url, file_path):
    response = requests.get(url + file_path)
    response.raise_for_status()
    return response.text

def send_notification(subject, body):
    message = f'Subject: {subject}\n\n{body}'
    with smtplib.SMTP(SMTP_SERVER, 587) as server:
        server.ehlo()
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, message)

on_start()

while True:
    for url in WEBSITE_LINKS:
        if url not in WEBSITE_CONTENTS:
            WEBSITE_CONTENTS[url] = {}
        for file_path in get_website_files(url):
            if file_path not in WEBSITE_CONTENTS[url]:
                try:
                    contents = get_file_contents(url, file_path)
                    WEBSITE_CONTENTS[url][file_path] = contents
                except Exception as e:
                    logging.error(f'Error getting file contents: {e}')
            else:
                try:
                    current_contents = get_file_contents(url, file_path)
                    if WEBSITE_CONTENTS[url][file_path] != current_contents:
                        changes = list(ndiff(WEBSITE_CONTENTS[url][file_path], current_contents))
                        changes_str = '\n'.join(changes)
                        subject = f'Update on {url}/{file_path}'
                        body = f'The contents of {url}/{file_path} have changed.\n\nChanges:\n\n{changes_str}'
                        try:
                            send_notification(subject, body)
                            logging.info('Email notification sent successfully.')
                        except Exception as e:
                            logging.error(f'Error sending email notification: {e}')
                        WEBSITE_CONTENTS[url][file_path] = current_contents
                except Exception as e:
                    logging.error(f'Error getting file contents: {e}')
        time.sleep(int(SCRAPE_FREQUENCY))