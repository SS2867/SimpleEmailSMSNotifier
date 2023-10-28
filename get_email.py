import imaplib, smtplib
import email
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time, datetime
import pytz
from Encryptor import decrypt
import os, importlib
import utils
import config
import bs4, requests
import json
import threading
#from twilio.rest import Client
from collections import defaultdict

for d in ["inbox_eml", "inbox_text"]:
    if not (os.path.exists(d) and os.path.isdir(d)):
        os.mkdir(d)

class Email_Service():
    def __init__(self):
        self.email_cache = {}
        self.email_download_list = defaultdict(int)
        self.extract_text_from_email_process_lock = False
        self.extract_text_from_email_process_lock_waiting = False
        self.smtp_server = None


    def login_email_server(self):
        global mail, username
        username = config.IMAP_USERNAME
        # create an IMAP4 class with SSL
        utils.logging(f"Logging in as {username}")
        mail = imaplib.IMAP4_SSL(config.IMAP_SERVER)
        # authenticate
        mail.login(username, decrypt(config.IMAP_PW, config.IMAP_PW_KEY))
        utils.logging(f"Logged in")

        if self.email_download_list:
            utils.logging(f"Unfinished email found: {dict(self.email_download_list.items())}")
            self.email_download_list.clear()
            #self.fetch_email(mark="", start_unfinished=True)



    def fetch_email(self, num=2, mark="(UNSEEN)", write=True,
                    trigger_extract=True, start_unfinished=False):
        if mark:
            utils.logging(f"Fetch: {username}", fold_repeat=config.LOGGING_FOLD_REPEAT_LENGTH)
            # search for specific mail by sender
            try:
                mail.select("inbox")
                result, data = mail.uid('search', None, mark) # (UNSEEN) marks the mail as read
            except (imaplib.IMAP4.abort, ConnectionResetError):
                self.login_email_server()
                return None
        else: data=[""]
        # if there is any mail
        if write:
            email_uid = data[0].split()
            if start_unfinished:
                email_uid += list(self.email_download_list)
            start_time, download_logging_time, download_elapsed_time = time.time(), 0, 0
            while email_uid and num>len(self.email_download_list):
                latest_email_uid = email_uid[-1]
                if self.email_download_list.get(latest_email_uid, 0) >= config.EMAIL_DOWNLOAD_MAX_RETRY:
                    #try:
                        self.email_download_list.pop(latest_email_uid)
                    #except: pass
                else:
                    threading.Thread(target=self.download_email,
                        args=(latest_email_uid, trigger_extract)).start()
                email_uid = email_uid[:-1]
            while self.email_download_list:
                download_elapsed_time = time.time() - start_time
                if download_elapsed_time>(download_logging_time+1):
                    download_logging_time = download_elapsed_time
                    utils.logging(f"Wait .eml download. uid:{dict(self.email_download_list.items())}",
                        fold_repeat=config.LOGGING_FOLD_REPEAT_LENGTH)
                if download_elapsed_time > config.EMAIL_DOWNLOAD_TIMEOUT:
                    utils.logging("Email batch download timeout, abort and relogin.")
                    self.login_email_server()
                    return data[0]
                time.sleep(.01)
            if data[0] or start_unfinished:
                utils.logging(f"Email batch downloaded in {str(download_elapsed_time)[:4]}s")
        return data[0]

    def download_email(self, uid, trigger_extract=True, write=True):
        self.email_download_list[uid]+=1

        utils.logging(f"Downloading email (uid:{uid})")

        result, email_data = mail.uid('fetch', uid, '(BODY[])') # Fetch the whole email body
        try:
            raw_email = email_data[0][1]
            assert type(raw_email) in (str, bytes)
        except (TypeError, AssertionError):
            utils.logging(f"Email (uid:{uid}) download failed. email_data:"
                f" {utils.summary_list(email_data)}")
        else:
            # write the raw email data to .eml file
            if write:
                with open(f'inbox_eml/{datetime.datetime.now().strftime("%y%m%d-%H%M%S")}.eml',
                           'wb') as f:
                    f.write(raw_email)
                utils.logging(f"Email (uid:{uid}) downloaded")
            else:
                utils.logging(f"Email (uid:{uid}) downloaded but is not written")
            if trigger_extract:
                threading.Thread(target=self.extract_text_from_email, args=(True,True,False,True)).start()

        try: self.email_download_list.pop(uid)
        except KeyError: pass




    def extract_text_from_email(self, targeting=False, write=True, force_all=False, debug=False):
        for i in range(8):
            if self.extract_text_from_email_process_lock_waiting:
                if debug:utils.logging("extract_text_from_email: another process waiting, Aborted")
                return
            else: time.sleep(.001)

        for i in range(4):
            if not self.extract_text_from_email_process_lock: time.sleep(.001)
            else: break
        for i in range(2000):
            if self.extract_text_from_email_process_lock:
                self.extract_text_from_email_process_lock_waiting = True
                if i%200==0 and debug:
                    utils.logging("extract_text_from_email: process locked, wait..",
                        fold_repeat=config.LOGGING_FOLD_REPEAT_LENGTH)
                time.sleep(.001)
            else:
                if i: utils.logging(f"extract_text_from_email: process lock got in the {i+1} th attempt.")
                break

        self.extract_text_from_email_process_lock = True
        self.extract_text_from_email_process_lock_waiting = False
        if debug:utils.logging(f"extract_text_from_email: started. "
            f"targeting={targeting}, write={write}, force_all={force_all}, debug={debug}")
        for filename in os.listdir("inbox_eml")[:]:
            if not filename.endswith(".eml") or os.path.isdir("inbox_eml/"+filename):
                continue

            with open("inbox_eml/"+filename) as f:
                content = "".join(f.readlines()).strip("\n ")
            if content.endswith("@@ Extracted by Reader @@") and not force_all:
                continue
            utils.logging(f"extract_text_from_email: {filename}")
            message = email.message_from_string(content)
            subject = decode_header(message['Subject'])[0][0]
            if isinstance(subject, bytes):
                subject = utils.decode_text(subject, "utf-8")
            send_time = email.utils.parsedate_to_datetime(message['Date'])
            send_time = send_time.astimezone(pytz.utc) + datetime.timedelta(hours=8)  # 转换为UTC时间
            send_time = send_time.strftime("%Y-%m-%d %H:%M:%S")
            sender = decode_header(message['From'])[0][0]
            if isinstance(sender, bytes):
                sender = utils.decode_text(sender, "utf-8")
            pure_text = ""
            for part in message.walk():
                if part.get_content_type().startswith('text/plain'):
                    charset = part.get_content_charset()
                    if charset is None:
                        charset = 'utf-8'
                    text = part.get_payload(decode=True)
                    decoded_text = utils.decode_text(text, charset)
                    if part.get_content_type().startswith('text/html'):
                        soup = bs4.BeautifulSoup(decoded_text, 'lxml')
                        decoded_text = '\n'.join([tag.get_text() for tag in soup.find_all(['p', 'h1', 'h2', 'a'])])
                    for i in "00000":
                        decoded_text = decoded_text.replace("\r", "").\
                            replace("\n\n\n", "\n\n").replace("\n\n ", "\n\n")
                    pure_text += decoded_text

            data = f"From: {sender}\nSubject: {subject}\nSend at: {send_time} HKT\n\nBody:\n\n{pure_text}"
            mail_hash = data.split("Body")[0].split("Subject: ")[1].replace(" ", "").\
                replace("\n", "").replace("\"", "").replace("'", "").replace("\t", "")
            mail_hash = utils.sha256(mail_hash)

            for key, value in self.email_cache.copy().items():
                if time.time() - value > config.EMAIL_CACHE_TIME:
                    self.email_cache.pop(key)

            if (mail_hash in self.email_cache) and (
                time.time() - self.email_cache.get(mail_hash, 0) < config.EMAIL_CACHE_TIME):
                with open("inbox_eml/"+filename, "a") as f:
                    f.write("\n\n@@ Extracted by Reader @@\n")
                continue

            _ = pure_text
            for i in "\n\t\r ~!@#$%^&*()_+{}|:\",./;'[]\=-<>?": _=_.replace(i, "")
            if len(_)<10:
                with open("inbox_eml/"+filename, "a") as f:
                    f.write("\n\n@@ Extracted by Reader @@\n")
                continue

            self.email_cache[mail_hash] = time.time()

            selector = target_email_selector(sender, subject, pure_text)

            if selector:
                if targeting:
                    utils.logging(f"@@email <{subject[:40]}> targeted")
                    threading.Thread(target=target_selected_action, args=(
                        sender, subject, pure_text)).start()
                else:
                    utils.logging(f"@@email <{subject[:40]}> targeted, however skipped action")
            if write:
                subject_fname = subject
                for c in "|\/?<>*'\":\n\t\r":
                    subject_fname = subject_fname.replace(c, "")
                with open("inbox_text/"+filename.split(".")[0]+f"_{subject_fname[:15]}.txt", "w") as f:
                    f.write(f"{selector}\n\n{data}")
                with open("inbox_eml/"+filename, "a") as f:
                    f.write("\n\n@@ Extracted by Reader @@\n")

        if debug:utils.logging("extract_text_from_email: finish")
        self.extract_text_from_email_process_lock = False

class SMTP_Service():
    def smtp_login(self, username=config.SMTP_USERNAME,
                   password=decrypt(config.SMTP_PW, config.SMTP_PW_KEY),
                   server=config.SMTP_SERVER,
                   port=config.SMTP_PORT):
        utils.logging("SMTP session creating")
        for i in range(4):
            if self.login_lock:
                while self.login_lock:
                    time.sleep(0.001)
                return
            time.sleep(0.001)
        self.login_lock = True

        if self.smtp_server:
            self.smtp_server.quit()
        self.smtp_server = smtplib.SMTP(server, port)
        self.smtp_server.starttls()
        self.smtp_server.login(username, password)

        self.login_lock = True

    def __init__(self, to="", body="", subject="", standby=False, login=True):
        self.smtp_server = None
        self.login_lock = False
        if not standby or login:
            self.smtp_login(config.SMTP_USERNAME,
                            decrypt(config.SMTP_PW, config.SMTP_PW_KEY),\
                            config.SMTP_SERVER,  config.SMTP_PORT)
        if not standby:
            self.send_email(to, body, subject)
    def send_email(self, to, body, subject="") -> int or str:
        utils.logging(f"email sending")
        SENDER_EMAIL = config.SMTP_DEFAULT_SENDER_EMAIL
        RECIPIENT_EMAIL = to
        SUBJECT = subject
        MESSAGE = body
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECIPIENT_EMAIL
        msg['Subject'] = SUBJECT
        msg.attach(MIMEText(MESSAGE, 'plain'))
        try:
            if not self.smtp_server:
                self.smtp_login(config.SMTP_USERNAME,
                                decrypt(config.SMTP_PW, config.SMTP_PW_KEY),\
                                config.SMTP_SERVER,  config.SMTP_PORT)
            self.smtp_server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
            self.smtp_server.quit()
            self.smtp_server = None
            utils.logging(f"email with subject <{subject[:30]}> sent")
            return 0
        except Exception as e:
            utils.logging(f"email <{subject[:30]}> failed to send")
            return str(e)

mail_session = Email_Service()

def target_selected_action(sender, subject, mail_body ):
    try:
        threading.Thread(target=send_sms,
            args=(config.SMS_SENDING_TO, config.SMS_PREMESSAGE(time.time(), subject),
                  config.SMS_DEFAULT_USE, config.SMS_SENDING_TIMING, True)).start()
    except Exception as e:
        threading.Thread(target=SMTP_Service, args=(config.EMAIL_DEFAULT_TO,
            config.MAIL_SMSERRORMESSAGE(time.time(), str(e)))).start()
        utils.logging(f"[Error] {config.MAIL_SMSERRORMESSAGE(time.time(), str(e))}")
    try:
        threading.Thread(target=make_call,
            args=(config.CALL_TO,)).start()
    except Exception as e:
        threading.Thread(target=SMTP_Service, args=(config.EMAIL_DEFAULT_TO,
            config.MAIL_CALLERRORMESSAGE(time.time(), str(e)))).start()
        utils.logging(f"[Error] {config.MAIL_CALLERRORMESSAGE(time.time(), str(e))}")
    def request_GPT_and_send(system_prompt=config.GPT_SYSTEM_PROMPT, top_p=0.8, max_tokens=400):
        try:
            SMTP_session = SMTP_Service(standby=True, login=False)
            threading.Thread(target=SMTP_session.smtp_login).start()
            GPT_response = request_GPT(system_prompt,
                utils.remove_urls(mail_body), top_p=top_p, max_tokens=max_tokens)
            threading.Thread(target=SMTP_session.send_email, args=(config.EMAIL_DEFAULT_TO,
                config.GPT_RESPONSE_POST_PROCESS(GPT_response.json().get("choices")[0].get("message").\
                get("content")))).start()
        except Exception as e:
            threading.Thread(target=SMTP_Service, args=(config.EMAIL_DEFAULT_TO,
                config.MAIL_GPTERRORMESSAGE(time.time(), str(e)))).start()
            utils.logging(f"[Error] {config.MAIL_GPTERRORMESSAGE(time.time(), str(e))}")
    #threading.Thread(target=request_GPT_and_send, args=(config.GPT_SYSTEM_PROMPT, 0.8, 300)).start()
    threading.Thread(target=request_GPT_and_send, args=(config.GPT_SYSTEM_PROMPT_INSTANT, 0.5, 100)).start()
    try:
        WebDav_Session = WebDav_Service()
        WebDav_Session.download(config.REMOTE_PATH, config.LOCAL_PATH)
        IoT_conf = utils.Config(config.LOCAL_PATH)
        IoT_conf.set("NOTIFICATION_FLAG", "mail_notification", True)
        WebDav_Session.upload(config.REMOTE_PATH, config.LOCAL_PATH)
    except Exception as e:
        threading.Thread(target=SMTP_Service, args=(config.EMAIL_DEFAULT_TO,
            config.MAIL_WEBDAVERRORMESSAGE(time.time(), str(e)))).start()
        utils.logging(f"[Error] {config.MAIL_WEBDAVERRORMESSAGE(time.time(), str(e))}")


def target_email_selector(sender, subject, text):
    global config
    config = importlib.reload(config)
    sender_score = config.SENDER_SELECTOR(sender)
    subject_score = config.SUBJECT_SELECTOR(subject)
    text_score = config.TEXT_SELECTOR(text)
    return (f"@@Target Detected! Score: Sender {sender_score},"+
        f"Subject {subject_score}, Text {text_score}"
        if config.SELECTOR(sender, subject, text) else "")


def request_GPT(system="", user="", max_tokens=400, temperature=0.7, top_p=0.3):
    utils.logging(f"GPT request posting. System: `{system[:55]}`, "
        f"user: `{user[:55]}`, max_tokens={max_tokens}, "
        f"temperature={temperature}, top_p={top_p}")
    utils.logging(f"GPT request posting. System: ```{system}```, "
        f"user: ```{user}```, max_tokens={max_tokens}, "
        f"temperature={temperature}, top_p={top_p}", dest="GPT_request.log", printout=False)
    start_time = time.time()
    url = "https://oa.api2d.net/v1/chat/completions"
    payload = json.dumps({
       "model": "gpt-3.5-turbo",
       "temperature": temperature,
       "top_p": top_p,
       "max_tokens": max_tokens,
       "messages": [
            {
            "role": "system",
            "content": system
            },
            {
            "role": "user",
            "content": user
            }
       ],
       "safe_mode": False
    })
    headers = {
       'Authorization':"Bearer "+decrypt(config.API2D_ACCOUNT_CREDENTIAL, config.API2D_ACCOUNT_CREDENTIAL_KEY),
       'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
       'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    usage = response.json().get("usage", {})
    try:
        utils.logging(f"GPT response got in {str(time.time()-start_time)[:4]}s. Content: "
            f'`{response.json().get("choices")[0].get("message").get("content")[:80]}`, '
            f'Prompt_token: {usage.get("prompt_tokens", "invalid")}, '
            f'Completion_token: {usage.get("completion_tokens", "invalid")}, '
            f'Credit_usage: {usage.get("final_total", "invalid")}, ')
        utils.logging(f"GPT response got in {str(time.time()-start_time)[:4]}s. Content: "
            f'`{response.json().get("choices")[0].get("message").get("content")}`, '
            f'Prompt_token: {usage.get("prompt_tokens", "invalid")}, '
            f'Completion_token: {usage.get("completion_tokens", "invalid")}, '
            f'Credit_usage: {usage.get("final_total", "invalid")}, ', dest="GPT_request.log", printout=False)
    except:
        utils.logging("GPT response got. However response invalid: {utils.summary_list(respose, 25)}.")
        utils.logging("GPT response got. However response invalid: "
            "{respose}.", dest="GPT_request.log", printout=False)
    utils.logging("\n\n", dest="GPT_request.log", timestamp="", printout=False, format_escape=False)
    return response

def send_sms(to, body, use=config.SMS_DEFAULT_USE, timing=[0], ascii_only=False):
    response = []
    if ascii_only:
        body = "".join([i if i.isascii() else "^" for i in body])
    for i in range(0, max(timing)+1):
        if i not in timing:
            time.sleep(1)
            continue
        utils.logging(f"SMS requesting.")
        url = 'https://api.twilio.com/2010-04-01/Accounts/ACa22966d40518cb843736591a51345b3b/Messages.json'
        data = {
            'To': to,
            'From': use,
            'Body': body
        }
        auth = (config.SMS_ACCOUNT_ID,
            decrypt(config.SMS_ACCOUNT_PW, config.SMS_ACCOUNT_PW_KEY))

        response.append( requests.post(url, data=data, auth=auth) )
        utils.logging(f"SMS <{body[:40]}> requested. length={len(body)}.")
        if i != max(timing):
            time.sleep(1)
    return response

def make_call(to,
              content='http://demo.twilio.com/docs/voice.xml',
              use=config.CALL_DEFAULT_USE):
    utils.logging(f"Phone call requesting.")
    #client = Client(config.CALL_ACCOUNT_ID,
    #    decrypt(config.CALL_ACCOUNT_PW, config.CALL_ACCOUNT_PW_KEY))
    #call = client.calls.create(url=content, to=to, from_=use)
    utils.logging(f"Phone call to <{to}> requested.")
    return call





