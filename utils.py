import re
import base64
import bs4
from email.header import decode_header
import quopri
import datetime
import hashlib
import configparser
import os
sha256 = lambda x:hashlib.sha256(x.rstrip().lstrip().lower().\
    encode("utf-8")).hexdigest().upper()

def decode_base64(text, get=["decoded_text"]):
    text = text.strip("\n ")
    text = del_mulnewline_in_text(text)

    if not text.startswith("Content-Type:") and not text.startswith("Content-Type:"):
        text = """Content-Type: text/plain; charset="utf-8"
Content-Transfer-Encoding: base64\n\n""" + text
    if not text.endswith("="): text += "="
    content_type = re.search(r'Content-Type:.*?charset=([\w-]+)',
        text.replace("\'", "").replace("\"", ""), re.DOTALL).group(1)
    content_encoding = re.search(r'Content-Transfer-Encoding: (.*?)\n', text)

    def decode(text:str, encoding:str):
        if encoding == "quoted-printable":
            """decoded_text = "\n".join(text.split("\n")[3:])"""
            decoded_text = quopri.decodestring(
                "\n".join(text.split("\n")[3:]).strip("\n") ).decode(content_type)
        else:
            encoded_text = re.search(r'\n\n(.*)', text, re.DOTALL).group(1)
            decoded_text = base64.b64decode(encoded_text).decode(content_type)
            decoded_text = decoded_text.replace("\r", "")
        return decoded_text

    if content_encoding is not None:
        content_encoding = content_encoding.group(1)
        decoded_text = decode(text, content_encoding)
    else:
        try: decoded_text = decode(text, "base64")
        except UnicodeDecodeError:
            decoded_text = decode(text, "quoted-printable")
    for i in "00000":
        decoded_text = decoded_text.replace("\n\n\n", "\n\n")

    return_value = []
    for i in get:
        return_value.append(locals()[i])
    return return_value

def decode_subject(text: str):
    if not text.isascii():
        return text
    text = text.strip(" \n")
    if not text.startswith("=?") or not text.endswith("?="):
        return text
    text_list = list(filter(None, text.split("\n")))
    result = []
    for i in text_list:
        decoded_parts = decode_header(i)
        decoded_text = ''.join([part[0].decode(part[1])
                if isinstance(part[0], bytes) else part[0]
                for part in decoded_parts])
        result.append(decoded_text)
    """result = [ (decode_base64(i.strip("\n\t?= ").split("?")[-1])[0]
        if "Q" not in i.strip("\n\t?= ").split("?")
        else i.strip("\n\t?= ").split("?")[-1])
        for i in text_list]"""
    return "".join(result)

def decode_text(text, encoding):
    try:
        decoded_text = text.decode(encoding)
    except UnicodeDecodeError:
        decoded_text = text.decode('utf-8', 'ignore')
    return decoded_text

def del_mulnewline_in_text(text):
    text_oddline = [_ for i, _ in enumerate(text.split("\n"),1) if i%2]
    text_evenline = [_ for i, _ in enumerate(text.split("\n"),0) if i%2]

    text_oddline_allblank = text_evenline_allblank = True
    for i in text_oddline:
        if (i.strip()):
            text_oddline_allblank = False
    for i in text_evenline:
        if (i.strip()):
            text_evenline_allblank = False

    if text_evenline_allblank:
        return "\n".join(text_oddline)
    elif text_oddline_allblank:
        return "\n".join(text_evenline)
    else:
        return text

def extract_fields(text: str, prefix: list, suffix:list=None, default=[]) -> list:
    result_start = re.split("|".join(prefix), text)[1:]
    result_start = list(filter(None, result_start))
    result = []
    for i in result_start:
        result.append(re.split("|".join(suffix), i)[0])
    return (result if result else default)

summary_list = lambda x, length=200: (([summary_list(i) if type(i) in (list, set, tuple)
    else (i[:length] if type(i) in (bytes, str) else i) for i in x])
    if type(x) in (list, tuple, set) else x)


def get_from_range(current_time:float or int, INBOX_CHECK_INTERVAL:dict) -> int:
    current_time = int(current_time)
    for time_range, interval in INBOX_CHECK_INTERVAL.items():
        if current_time in time_range:
            return interval
    return None

time_to_UTC_range = (lambda h1, m1, h2, m2:
    range((h1)*3600+m1*60, (h2)*3600+m2*60))

format_time = lambda x:datetime.datetime.now().strftime(x)

def logging(content, dest="main.log", printout=True, timestamp='%m%d-%H:%M:%S',
            format_escape=True, fold_repeat=0):
    content = str(content)
    if format_escape:
        content = content.replace("\n", r"\n").replace("\r", r"\r").replace("\t", r"\t")
    fold = False
    if fold_repeat:
        if not os.path.exists(dest):
            open(dest, "w").close()
        with open(dest) as f:
            lastline = "".join(f.readlines()).strip("\n ").split("\n")[-1]
            if content in lastline and len(lastline)<fold_repeat:
                fold = True
    if timestamp:
        content = format_time(timestamp+" ") + content
    if printout:
        print(content)
    with open(dest, "a") as f:
        if fold:
            f.write(f" ~{format_time('%M:%S')[1:]}")
        else:
            f.write("\n"+str(content) + ("  " if fold_repeat else "") )

def remove_urls(text):
    url_pattern = re.compile(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),\n\t\r]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")
    result = re.sub(url_pattern, '', text)
    return result

class Config:
    _rub = iter('}${0JPY*S\\|@>hSO\\{dB&fD}=bP[5EyN=`[~3o2LVgk2/p3X*4')
    def __init__(self, filename):
        self.filename=filename
        if not os.path.exists(filename):
            open(filename, "w").close()
        self.read()
    def read(self):
        self.config = configparser.ConfigParser()
        self.config.read(self.filename)
    def get(self, section_name, option_name, default=_rub,
            dtype=str, refresh=True):
        if refresh:
            self.read()
        if default == self._rub:
            result = self.config.get(section_name, option_name)
        else:
            try:
                result = self.config.get(section_name, option_name)
            except:
                return default
        if dtype==str: return str(result)
        elif dtype==int: return int(result)
        elif dtype==bool:
            return ((result.lower() == 'true') if
                result.lower() in ["true", "false"] else result)
        elif dtype==float: return float(result)
        else: return result
    def set(self, section_name, option_name, value, refresh_first=True,
            write=True):
        if refresh_first:
            self.read()
        self.config.set(section_name, option_name, str(value))
        if write:
            self.write()
    def write(self):
        with open(self.filename, 'w') as configfile:
            self.config.write(configfile)

def truncate_string(string, length=40, ratio=(1, 1)):
    if len(string) <= length:
        return string
    else:
        n = (length - 3) // sum(ratio)
        return string[:n*ratio[0]] + "..." + string[-n*ratio[1]:]


if __name__ == "__main__":
    text = """Content-Type: text/plain; charset=utf-8


=E6=88=91=E4=BB=AC=E5=A7=8B=E7=BB=88=E5=9C=A8=E5=8A=AA=E5=8A=9B=E8=AE=A9Sup=
ercell
    """

    print(decode_base64(text))