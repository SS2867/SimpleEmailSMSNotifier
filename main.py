import get_email
import time, datetime
import config
import os
import utils
import sys
import imaplib
import random
from threading import Thread

def selfcheck(debug=False, fast_check=False):
    status_OK = GPT_status_OK = SMTP_status_OK = IMAP_status_OK =\
        SMS_status_OK = call_status_OK = webdav_status_OK = PU_HTTP_OK = True
    selfcheck_alert = {}

    utils.logging(f"[selfcheck] Selfcheck started"+(" (fast mode)" if fast_check else ""))



    if fast_check:
        utils.logging(f"[selfcheck] GPT check skipped")
        GPT_result = "GPT Skipped\n"
        GPT_response_time = "Skipped"
    else:
        utils.logging(f"[selfcheck] checking GPT function")
        try:
            start_time = time.time()
            GPT_response = get_email.request_GPT("", "Say \"Hi\" to me 4 times, then"+
                " tell me a short story.", max_tokens=(65 if fast_check else 165))
            assert "Hi" in GPT_response.json()["choices"][0]["message"]["content"]
            GPT_response_time = (str(time.time()-start_time)[:4]+
                f" /{GPT_response.json()['usage']['completion_tokens']}")
            if float(time.time()-start_time) > 9:
                selfcheck_alert["GPT"] = ("GPT takes "
                    f"{GPT_response_time} to get response, performance impacted!")
            GPT_result = (f"{utils.format_time('%H:%M:%S')}: [Info] GPT OK."+
                " Time in sec: "+GPT_response_time+"\n")
        except Exception as e:
            try:
                status_OK = GPT_status_OK = False
                GPT_result = (f"{utils.format_time('%H:%M:%S')}: [Error] GPT "+
                    "error. Exception "+f"{str(e)}. Response {GPT_response.json()}"+"\n")
            except UnboundLocalError:
                GPT_result = (f"{utils.format_time('%H:%M:%S')}: [Error] GPT "+
                    "error. Exception "+f"{str(e)}. GPT_response failed to get." +"\n")
        with open("selfcheck.log", "a") as f:
            f.write(utils.format_time('%m-%d')+" "+GPT_result)
        utils.logging(f"[selfcheck] "+GPT_result)

    if not fast_check:
        time.sleep(5)

    utils.logging(f"[selfcheck] checking IMAP&MailExtract function")
    try:
        if not fast_check:
            start_time = time.time()
            for i in range(3):
                get_email.mail_session.extract_text_from_email(targeting=False, write=False)
            extract_time = ( time.time()-start_time ) / 3
            utils.logging(f"[selfcheck] mail extract takes {int(extract_time*1000)}ms")
            if extract_time>0.3:
                selfcheck_alert["extract"] = (f"mail extract takes {int(extract_time*1000)}ms"
                    ", performance impacted!")

        start_time = time.time()
        IMAP_data = ""
        IMAP_data = get_email.mail_session.fetch_email(num=1, mark="(SEEN)", write=True, trigger_extract=False)
        assert IMAP_data
        get_email.mail_session.extract_text_from_email(targeting=False, write=True, debug=True)
        IMAP_response_time = str(time.time()-start_time)[:4]
        if float(IMAP_response_time) > 6:
            selfcheck_alert["IMAP/MailExtract"] = ("IMAP/MailExtract takes "
                f"{IMAP_response_time}s, IMAP performance not good!")
        IMAP_extract_result = (f"{utils.format_time('%H:%M:%S')}: [Info] IMAP/MailExtract"+
            " OK. Time in sec: "+IMAP_response_time+"\n")
    except Exception as e:
        status_OK = IMAP_status_OK = False
        try:
            IMAP_extract_result = (f"{utils.format_time('%H:%M:%S')}: [Error] "+
                f"IMAP/MailExtract error. Exception {str(e)}. IMAP_data: {IMAP_data}\n")
        except UnboundLocalError:
            IMAP_extract_result = (f"{utils.format_time('%H:%M:%S')}: [Error] "+
                f"IMAP/MailExtract error. Exception {str(e)}. IMAP_data: failed to get.\n")
    with open("selfcheck.log", "a") as f:
        f.write(utils.format_time('%m-%d')+" "+IMAP_extract_result)
    utils.logging("[selfcheck] "+IMAP_extract_result)


    time.sleep((0 if fast_check else 5))

    utils.logging(f"[selfcheck] checking SMTP function")
    try:
        start_time = time.time()
        SMTP_session = get_email.SMTP_Service(standby=True)
        send_email_response = SMTP_session.send_email(config.EMAIL_DEFAULT_TO,
            "".join([GPT_result, IMAP_extract_result])+
            f"\nSend at {utils.format_time('%H:%M:%S')}",
            "system check"+("" if status_OK else " ERROR!") )
        assert send_email_response == 0
        SMTP_response_time = str(time.time()-start_time)[:4]
        if float(SMTP_response_time) > 3.6:
            selfcheck_alert["SMTP"] = ("SMTP takes "
                f"{SMTP_response_time}s to send, performance impacted!")
        SMTP_result = (f"{utils.format_time('%H:%M:%S')}: [Info] SMTP"+
            " OK. Time in sec: "+SMTP_response_time+"\n")
    except Exception as e:
        status_OK = SMTP_status_OK = False
        try:
            SMTP_result = (f"{utils.format_time('%H:%M:%S')}: [Error] SMTP "+
                f"error. Exception {str(e)}. Response {send_email_response}"+"\n")
        except UnboundLocalError:
            SMTP_result = (f"{utils.format_time('%H:%M:%S')}: [Error] SMTP "+
                f"error. Exception {str(e)}. send_email_response failed to get"+"\n")
    with open("selfcheck.log", "a") as f:
        f.write(utils.format_time('%m-%d')+" "+SMTP_result)
    utils.logging("[selfcheck] "+ SMTP_result)


    summary = (f"GPT: {GPT_response_time if GPT_status_OK else 'Error'}\n"+
                f"IMAP: {IMAP_response_time if IMAP_status_OK else 'Error'}\n"+
                f"SMTP: {SMTP_response_time if SMTP_status_OK else 'Error'}\n"+
                f"{len(selfcheck_alert)} Alert\n")
    if not fast_check:
        time.sleep(5)

        utils.logging(f"[selfcheck] checking SMS sending function")
        try:
            if not debug:
                while time.time()%86400 < config.DAILY_SELFCHECK_SMS_SEC:
                    time.sleep(.01)
            summary += f"Sent at {utils.format_time('%H:%M:%S')} HKT"
            get_email.send_sms( config.SMS_SENDING_TO,
                "==SRS System==\n"+f"Overall: {status_OK}\n"+ summary )
            SMS_result = (f"{utils.format_time('%H:%M:%S')}: [Info] SMS Sending OK.\n")
        except Exception as e:
            SMS_status_OK = status_OK = False
            SMS_result = (f"{utils.format_time('%H:%M:%S')}: [Error] SMS Sending error."
                f" Exception {str(e)}.\n")
    else:
        SMS_result = (f"{utils.format_time('%H:%M:%S')}: [Debug] SMS test skipped.\n")
    with open("selfcheck.log", "a") as f:
        f.write(utils.format_time('%m-%d')+" "+SMS_result)
    utils.logging("[selfcheck] "+SMS_result)

    summary += f"\nSMS: {SMS_status_OK}\nOverall: {status_OK}\n"
    email_alert_report = ""
    if selfcheck_alert:
            for item, description in selfcheck_alert.items():
                utils.logging(f"[selfcheck] [Alert] {item}: {description}")
                email_alert_report += f"{item}: {description}\n"
    if not (call_status_OK and SMS_status_OK):
        get_email.SMTP_Service(config.EMAIL_DEFAULT_TO, summary+
            (f"\nAlert:\n{email_alert_report}" if email_alert_report else "")+
            f"\nSend at {utils.format_time('%H:%M:%S')}",
            "system check ERROR!")
    elif selfcheck_alert:
        get_email.SMTP_Service(config.EMAIL_DEFAULT_TO, summary+
            (f"\nAlert:\n{email_alert_report}" if email_alert_report else "")+
            f"\nSend at {utils.format_time('%H:%M:%S')}",
            "system check alert")

    with open("selfcheck.log", "a") as f:
        f.write(utils.format_time('%m-%d')+" "+f"Overall: {status_OK}\n\n")
    utils.logging(f"[selfcheck] Finished. Overall status: {status_OK}")
    return status_OK


get_email.mail_session.login_email_server()

options = sys.argv[1:]
for option in options:
    if option in ( "-fc" or "--fastcheck"):
        system_status = selfcheck(True, True)
    elif option in ( "-c" or "--check"):
        system_status = selfcheck(True)


last_check_email_time = 0
while 1:
    current_time = time.time()
    current_second_in_day = time.time()%86400
    try:
        if abs(current_second_in_day - config.DAILY_SELFCHECK_SEC) <=5:
            time.sleep(10)
            selfcheck()
            time.sleep(10)
        elif sum([ bool(abs(current_second_in_day-i)<=5)
                   for i in config.DAILY_SELFCHECK_QUICK_SEC]):
            time.sleep(5)
            selfcheck(fast_check=True)
            time.sleep(4)
        elif time.time() - last_check_email_time > utils.get_from_range(
            current_second_in_day, config.INBOX_CHECK_INTERVAL):
            last_check_email_time = time.time()
            get_email.mail_session.fetch_email()
            get_email.mail_session.extract_text_from_email(targeting=True)
    except (imaplib.IMAP4.abort, ConnectionResetError):
        get_email.mail_session.login_email_server()

    if random.randint(0,50) == 0:
        if os.path.exists("exit_main"):
            os.remove("exit_main")
            utils.logging("File `exit_main` captured, main program exiting.")
            break
    time.sleep(0.01)









