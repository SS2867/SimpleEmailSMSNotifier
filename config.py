

import utils
import os
import random

LOGGING_FOLD_REPEAT_LENGTH = 79

target_sender_list = [
    "vip1@example.com",
    "vip2@example.com",
    "vip3@example.com",
    "alert@example.com",
    "admin@example.com"
]
exclude_sender_list = [
    "do.not.reply@example.com",
    "daily.summary@example.com",
]

SENDER_SELECTOR = lambda x: sum([(i.lower() in x.lower()) for i in target_sender_list])

SENDER_DESELECTOR = lambda x: sum([(i.lower() in x.lower()) for i in exclude_sender_list])

target_subject_list = [
    "Phishing Alert", "Warning", "important", "New pending order", "emergency",
]

SUBJECT_SELECTOR = lambda x: sum([(i.lower() in x.lower()) for i in target_subject_list])

target_text_list = [
    "Phishing Alert", "Warning", "important", "New pending order", "emergency",
]

TEXT_SELECTOR =lambda x: sum([(i.lower() in x.lower()) for i in target_text_list])

EMAIL_CACHE_TIME = 40
EMAIL_DOWNLOAD_TIMEOUT = 16
EMAIL_DOWNLOAD_MAX_RETRY = 1
IMAP_SERVER = 'imap.gmail.com'
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_DEFAULT_SENDER_EMAIL = SMTP_USERNAME = IMAP_USERNAME = 'SENDER_EMAIL'
SMTP_PW, SMTP_PW_KEY = IMAP_PW, IMAP_PW_KEY = 'PW', "key"

EMAIL_DEFAULT_TO = "your.email@example.com"

SELECTOR = lambda sender, subject, text: (
    SENDER_SELECTOR(sender) or SUBJECT_SELECTOR(subject) or TEXT_SELECTOR(text)>1
    ) and not SENDER_DESELECTOR(sender)

SMS_PREMESSAGE = (lambda time, subject:
    f"==!Important Email Alert!==\nEmail <{subject[:40]}> detected at "+
    f"{utils.format_time('%H:%M:%S')} HKT!")

MAIL_GPTERRORMESSAGE = (lambda time, exception:
    f"SMSNotifier System Warning! GPT Exception: {exception} at "+
    f"{utils.format_time('%H:%M:%S')} HKT!")

MAIL_SMSERRORMESSAGE = (lambda time, exception:
    f"SMSNotifier System Warning! SMS sending Exception: {exception} at "+
    f"{utils.format_time('%H:%M:%S')} HKT!")

MAIL_CALLERRORMESSAGE = (lambda time, exception:
    f"SMSNotifier System Warning! Phone calling Exception: {exception} at "+
    f"{utils.format_time('%H:%M:%S')} HKT!")


SMS_SENDING_TIMING = [0]
SMS_SENDING_TO = CALL_TO = "+85291234567"
SMS_DEFAULT_USE = CALL_DEFAULT_USE = "+19876543210"
SMS_ACCOUNT_ID = CALL_ACCOUNT_ID = 'ACCOUNT_ID'
CALL_ACCOUNT_PW, CALL_ACCOUNT_PW_KEY = SMS_ACCOUNT_PW, SMS_ACCOUNT_PW_KEY = \
    'ACCOUNT_PW', "CALL_ACCOUNT_PW_KEY"

API2D_ACCOUNT_CREDENTIAL, API2D_ACCOUNT_CREDENTIAL_KEY = \
    'API2D_ACCOUNT_CREDENTIAL', "API2D_ACCOUNT_CREDENTIAL_KEY"

GPT_RESPONSE_POST_PROCESS = lambda x: x

GPT_SYSTEM_PROMPT = "<Depreciated>"

GPT_SYSTEM_PROMPT_INSTANT = """<Scenario to reply to an important targeted email>
Adhere to the following rules:
<rule1>
<rule2>
<rule3>
Use the following template:
```
[Recipient]:
  I am xxx. .....

Regards,
xxx
```
"""


DAILY_SELFCHECK_SEC = (24+7-8)*3600 - 90
DAILY_SELFCHECK_SMS_SEC = (24+7-8)*3600- 7
DAILY_SELFCHECK_QUICK_SEC = [(12-8)*3600, (16-8)*3600]

INBOX_CHECK_INTERVAL = {
    utils.time_to_UTC_range(1+16,30, 6+16,0)    :30,
    utils.time_to_UTC_range(6+16,0, 7+16,0)     :15,
    utils.time_to_UTC_range(7+16,0, 8+16,0)     :10,
    utils.time_to_UTC_range(8-8,0, 8-8,30)      :10,
    utils.time_to_UTC_range(8-8,30, 9-8,0)      :7,
    utils.time_to_UTC_range(9-8,0, 21-8,30)     :2,
    utils.time_to_UTC_range(21-8,30, 23-8,30)   :7,
    utils.time_to_UTC_range(23-8,30, 0+16,30)   :10,
    utils.time_to_UTC_range(0+16,30, 1+16,30)   :15,
}


