// ====== Start of Config ======
const SCAN_INTERVAL = 4600;  // in ms
const SCRIPT_TRIGGER_INTERVAL = 600000;   // in ms
const NOTIFICATION_COOLDOWN = 180000;   // in ms

const TARGET_SENDER_LIST = [
    "vip1@example.com",
    "vip2@example.com",
    "vip3@example.com",
    "alert@example.com",
    "admin@example.com"
];
const EXCLUDE_SENDER_LIST = [
    "do.not.reply@example.com",
    "daily.summary@example.com",
];
const SENDER_SELECTOR = (x) => {
    return TARGET_SENDER_LIST.reduce((score, sender) => {
        return score + (x.toLowerCase().includes(sender.toLowerCase()));
    }, 0);
};
const SENDER_DESELECTOR = (x) => {
    return EXCLUDE_SENDER_LIST.reduce((score, sender) => {
        return score + (x.toLowerCase().includes(sender.toLowerCase()));
    }, 0);
};
const TARGET_SUBJECT_LIST = [
    "Phishing Alert", "Warning", "important", "New pending order", "emergency",
];
const SUBJECT_SELECTOR = (x) => {
    return TARGET_SUBJECT_LIST.reduce((score, subject) => {
        return score + (x.toLowerCase().includes(subject.toLowerCase()));
    }, 0);
};
const TARGET_TEXT_LIST = [
    "Phishing Alert", "Warning", "important", "New pending order", "emergency",
];
const TEXT_SELECTOR = (x) => {
    return TARGET_TEXT_LIST.reduce((score, text) => {
        return score + (x.toLowerCase().includes(text.toLowerCase()));
    }, 0);
};
const SELECTOR = (sender, subject, text) => {
    //Logger.log(`sender ${SENDER_SELECTOR(sender)}, subject ${SUBJECT_SELECTOR(subject)}, text ${TEXT_SELECTOR(text)},desender ${SENDER_DESELECTOR(sender)}`  )
    return (SENDER_SELECTOR(sender) > 0 || SUBJECT_SELECTOR(subject) > 0 || TEXT_SELECTOR(text) > 1) &&
           (SENDER_DESELECTOR(sender) === 0);
};

const SMS_PREMESSAGE = (subject) => {
    return `"==!Email Alert!==\nEmail <${subject.slice(0,40)}> detected at ${new Date().toLocaleTimeString()}`
};
EMAIL_DEFAULT_TO = "your.email@example.com"
CHATBOT_SYSTEM_PROMPT = `<Scenario to reply to an important targeted email>
Adhere to the following rules:
<rule1>
<rule2>
<rule3>
Use the following template:
\`\`\`
[Recipient]:
  I am xxx. .....

Regards,
xxx
\`\`\``;
const CHATBOT_RESPONSE_POST_PROCESS = (x) => {return x.replaceAll("xxx", "Your Name")};
const API2D_ACCOUNT_CREDENTIAL = 'tc*4!5$V9cxaLaa8apWa3uO2THgQlwQku8Td*PU7i';
const API2D_ACCOUNT_CREDENTIAL_KEY = "R6QP6kAtnRgagzE7";
const SMS_ACCOUNT_ID = 'AC51ace336390d71448e0fda078efa6ca4';
const SMS_ACCOUNT_PW = "1GtlY0*bUjY7z!QCffcPGEI#TQXoiiao";
const SMS_ACCOUNT_PW_KEY = "ywX73q14";
const SMS_DEFAULT_USE = "+1888123456";
const SMS_SENDING_TO = ["+85291234567", "+12567654321"];
const CALL_DEFAULT_USE = "+1888123456";
const CALL_TO = ["+85291234567", "+12567654321"];
const CALL_ACCOUNT_ID = 'AC51ace336390d71448e0fda078efa6ca4';
const SMS_ACCOUNT_PW = "1GtlY0*bUjY7z!QCffcPGEI#TQXoiiao";
const CALL_ACCOUNT_PW_KEY = "ywX73q14";

// ====== End of Config ======

function checkUnreadEmails() {
  var scriptStartTime = new Date().getTime();
  var durationLimit = SCRIPT_TRIGGER_INTERVAL - 2500;    // in ms

  while (true){//for (var i = 0; i < 12; i++) {
    var scanStartTime = new Date().getTime();

    if (new Date().getTime() - scriptStartTime > durationLimit) { break;}  // Check whether exceed duration Limit

    Logger.log("Scanning");
    
    // Get unread emails (latest 3 unreads)
    //var threads = GmailApp.getInboxThreads(0, 6);
    //var unreadThreads = threads.filter(thread => thread.isUnread()).slice(0, 3);
    var unreadThreads = GmailApp.search('is:unread', 0, 2);

    unreadThreads.forEach(thread => {
      var messages = thread.getMessages();
      messages.forEach(message => {
        if (!message.isRead) {
          var subject = message.getSubject();
          var body = message.getBody();
          var from_ =  message.getFrom();
          var to = message.getTo();
          
          console.log(`Unread email: ${from_} | ${subject.slice(0,40)} | ` +
            `${body.slice(0,40).replaceAll("\n", "\\n")}`);
          if (targetEmailSelector(from_, to, body, subject)){
            targetSelectedAction(from_, subject, body);
          } 
          message.markRead();
        }
      });
    });

    Logger.log(`Scan complete in ${new Date().getTime()-scanStartTime}ms`);
    Utilities.sleep(Math.max(1000, SCAN_INTERVAL - (new Date().getTime()-scanStartTime)));
  }
}

const throttle = (func, wait = 100) => {
  let lastExec = 0;
  return (...args) => {
    const elapsed = Date.now() - lastExec;
    const later = () => {
      lastExec = Date.now();
      func.apply(this, args);
    };
    if (elapsed > wait) {
      later();
    }else{
      Logger.log(`Function func ${func} is throttled. Last exec ${lastExec}, wait=${wait}`)
    }
  };
};

function targetEmailSelector(from_, to, body, subject){
  /*const senderScore = SENDER_SELECTOR(from);
  const subjectScore = SUBJECT_SELECTOR(subject);
  const textScore = TEXT_SELECTOR(body);*/
  return SELECTOR(from_, subject, body) ? true : "";
};

const throttledNotify = throttle( ()=>{
  //for (i of SMS_SENDING_TO){ sendSMS(i, SMS_PREMESSAGE(subject), SMS_DEFAULT_USE, [0], true);  }
  for (i of CALL_TO){ makeCall(CALL_DEFAULT_USE, i);}
}, NOTIFICATION_COOLDOWN);
function targetSelectedAction(from_, subject, body){
  throttledNotify();
  var botResponse = requestChatBot(CHATBOT_SYSTEM_PROMPT, body) .choices[0].message.content;
  sendEmail(EMAIL_DEFAULT_TO, "", CHATBOT_RESPONSE_POST_PROCESS(botResponse));
}

function sendEmail(to, subject, body) {
  MailApp.sendEmail(to, subject, body);
}

function decrypt(cipherText, key, validChars = ' !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~') {
  for (let char of cipherText) {
    if (!validChars.includes(char)) {throw new Error(`Invalid character in ciphertext: ${char}`);}
  }
  let plainText = cipherText.split("");
  const opralen = Math.floor(0.1 * cipherText.length); // Operation length factor
  const txtlen = cipherText.length;
  // Iterate over the key in reverse order
  for (let index = key.length - 1; index >= 0; index--) {
    const i = key.charCodeAt(index) - 32;
    let temp = index + 3 + Math.floor(plainText.length * 1.1); // Operation factor temp
    // Exchange the position of two characters depending on operation factors
    for (let j = 0; j < 4 + Math.floor(plainText.length * 1.1); j++) {
      const factorA = (Math.pow(temp, 2) + opralen * temp) % txtlen;
      const factorB = (temp + 1 + key.charCodeAt(index)) % txtlen;
      [plainText[factorA], plainText[factorB]] = [plainText[factorB], plainText[factorA]];  // Swap characters
      temp -= 1;
    }
    // Reverse linear shifting using operation factors
    for (let j = plainText.length - 1; j >= 0; j--) {
      plainText[j] = validChars[
        ((validChars.indexOf(plainText[j]) - i - Math.floor(i/3) - Math.floor(i/17) - (index + 1) * (j + 2)) % validChars.length + validChars.length)%validChars.length 
      ];
      if (j > 0) {
        plainText[j] = validChars[
          ((validChars.indexOf(plainText[j]) - i -
            (index + 1 + validChars.indexOf(plainText[j - 1]) + 32) * (j + 2) 
          ) % validChars.length+validChars.length)%validChars.length
        ];
      }
    }
  }
  return plainText.join(""); // Convert the array back to a string
}


function requestChatBot(system = "", user = "", maxTokens = 400, temperature = 0.7, topP = 0.3) {
  const url = "https://oa.api2d.net/v1/chat/completions";
  const payload = {
      model: "gpt-3.5-turbo",
      temperature: temperature,
      top_p: topP,
      max_tokens: maxTokens,
      messages: [
          {role: "system", content: system},
          {role: "user", content: user}
      ],
      safe_mode: false
  };
  try {
      var options = {
        method: 'post',
        contentType: 'application/json',
        payload: JSON.stringify(payload)
      };
      options.headers = { 
        'Authorization': "Bearer "+decrypt(API2D_ACCOUNT_CREDENTIAL, API2D_ACCOUNT_CREDENTIAL_KEY),
      };
      var response = UrlFetchApp.fetch(url, options); // Make the POST request
      var data = JSON.parse(response.getContentText()); // Parse the JSON response
      const assistant = data.choices[0].message.content;
      const usage = data.usage || {};
      Logger.log(`Chatbot API requested. System: \`${system.slice(0,70).replaceAll("\n", "\\n")}\`, ` +
        `User: \`${user.slice(0,70).replaceAll("\n", "\\n")}\`, max_tokens=${maxTokens}, ` +
        `temperature=${temperature}, topP=${topP}, ` +
        `Response: \`${assistant.slice(0,70).replaceAll("\n", "\\n")}\`, usage=${usage}`);
      return data;
  } catch (error) {
      console.error("Error making Chatbot API request:", error);
      throw error;
  }
}

function sendSMS(to, body, use, timing = [0], asciiOnly = false) {
  const response = [];
  
  if (asciiOnly) {    body = body.split('').map(function(char) {
      return char.charCodeAt(0) < 128 ? char : '^';
    }).join('');  }

  for (let i = 0; i <= Math.max(...timing); i++) {
    if (!timing.includes(i)) {
      Utilities.sleep(1000); // Sleep for 1 second
      continue;
    }

    Logger.log("SMS requesting.");
    const url = `https://api.twilio.com/2010-04-01/Accounts/${SMS_ACCOUNT_ID}/Messages.json`;
    const payload = { 'To': to,  'From': use, 'Body': body };
    const options = {
      'method': 'post',
      'contentType': 'application/x-www-form-urlencoded',
      'payload': payload,
      'headers': {
        'Authorization': 'Basic ' + Utilities.base64Encode(SMS_ACCOUNT_ID + ':' + decrypt(SMS_ACCOUNT_PW, SMS_ACCOUNT_PW_KEY))
      }
    };
    const res = UrlFetchApp.fetch(url, options);
    response.push(res.getContentText());
    Logger.log(`SMS <${body.substring(0, 40).replaceAll("\n", "\\n")}> requested to ${to}. ` +
      `length=${body.length}.`);

    if (i !== Math.max(...timing)) {Utilities.sleep(1000); }
  }
  return response;
}

function makeCall(from_, to, content = "http://demo.twilio.com/docs/voice.xml") {
  const twilioUrl = `https://api.twilio.com/2010-04-01/Accounts/${CALL_ACCOUNT_ID}/Calls.json`;
  const payload ={From: from_,  To: to, Url: content};
  Logger.log(`Call to ${to} requesting.`);
  try {
    const response = UrlFetchApp.fetch(twilioUrl, {
      'method': 'POST',
      'headers': {
        'Authorization': 'Basic ' + Utilities.base64Encode(`${CALL_ACCOUNT_ID}:${decrypt(CALL_ACCOUNT_PW, CALL_ACCOUNT_PW_KEY)}`),
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      'payload': payload
    });
    Logger.log(`Call to ${to} successfully requested.`);
    return response;
  } catch (error) {
    console.error("Error making the call:", error);
    throw error;
  }
}

function main(){
  checkUnreadEmails();
}

function test(){

}



