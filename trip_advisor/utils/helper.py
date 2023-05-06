import boto3
import logging
import json
import os
from selenium.webdriver.chrome.options import Options

region = "eu-west-1"
ta_bucket = "trip-advisor-dev"
CHROMEDRIVER_PATH = "/opt/chromedriver"
CHROMIUM_PATH = "/opt/headless-chromium"


def _data_to_file(data, filename, extension):
    path = "/tmp/"
    filename_w_extension = filename
    if extension == "json":
        filename_w_extension += ".json"
        path += filename_w_extension
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({"restaurants": data}, f, ensure_ascii=False)
            f.close()
        return path, filename_w_extension
    return None, filename


def store_in_s3_bucket(bucket, s3_path, data, filename, extension="json"):
    s3_client = boto3.client('s3', region_name=region)
    path_file, filename_w_extension = _data_to_file(data, filename, extension)
    if path_file is None:
        logging.error("File extension selected is not available. Aborting saving")
        return
    s3_client.upload_file(path_file, bucket, f"{s3_path}/{filename_w_extension}")
    os.remove(path_file)


def set_chrome_options() -> Options:
    options = Options()
    options.binary_location = CHROMIUM_PATH
    options.add_argument('--autoplay-policy=user-gesture-required')
    options.add_argument('--disable-background-networking')
    options.add_argument('--disable-background-timer-throttling')
    options.add_argument('--disable-backgrounding-occluded-windows')
    options.add_argument('--disable-breakpad')
    options.add_argument('--disable-client-side-phishing-detection')
    options.add_argument('--disable-component-update')
    options.add_argument('--disable-default-apps')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-domain-reliability')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-features=AudioServiceOutOfProcess')
    options.add_argument('--disable-hang-monitor')
    options.add_argument('--disable-ipc-flooding-protection')
    options.add_argument('--disable-notifications')
    options.add_argument('--disable-offer-store-unmasked-wallet-cards')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--disable-print-preview')
    options.add_argument('--disable-prompt-on-repost')
    options.add_argument('--disable-renderer-backgrounding')
    options.add_argument('--disable-setuid-sandbox')
    options.add_argument('--disable-speech-api')
    options.add_argument('--disable-sync')
    options.add_argument('--disk-cache-size=33554432')
    options.add_argument('--hide-scrollbars')
    options.add_argument('--ignore-gpu-blacklist')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--metrics-recording-only')
    options.add_argument('--mute-audio')
    options.add_argument('--no-default-browser-check')
    options.add_argument('--no-first-run')
    options.add_argument('--no-pings')
    options.add_argument('--no-sandbox')
    options.add_argument('--no-zygote')
    options.add_argument('--password-store=basic')
    options.add_argument('--use-gl=swiftshader')
    options.add_argument('--use-mock-keychain')
    options.add_argument('--single-process')
    options.add_argument('--headless')
    options.add_argument('--window-size=1920x1080')
    options.add_argument('--user-data-dir={}'.format('/tmp/user-data'))
    options.add_argument('--data-path={}'.format('/tmp/data-path'))
    options.add_argument('--homedir={}'.format('/tmp'))
    options.add_argument('--disk-cache-dir={}'.format('/tmp/cache-dir'))
    return options
