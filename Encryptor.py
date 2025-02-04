#-------------------------------------------------------------------------------
# Name:        Encryptor
# Purpose:     Encrypt and decrypt data using a symmetric self-designed
#              cryptographic algorithm
#
# Author:
#
# Created:     30/10/2022
# Copyright:   (c) Steven Song 2022
# Licence:     <your licence>
#-------------------------------------------------------------------------------

def encryptRound(plainText, key, validChars=' !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~'):       # Encrypt a given plain text using a given key for one round
    if not plainText: return ""
    for i in plainText: assert i in validChars, f"Invalid character in plaintext: {i}"
    cipherText = list(plainText)            # Initialize the cipher text list
    opralen, txtlen = int(0.1*len(cipherText)), len(cipherText)
    for index, i in enumerate(key):         # Generate the operation factor index and i from the given key.
        i = ord(i)-32
        for j in range(len(cipherText)):
            cipherText[j] = validChars[(validChars.find(cipherText[j])+i+i//3+i//17+(index+1)*(j+2))%len(validChars)]      # Conduct linear shifting using operation factors.
            if j:
                cipherText[j] = validChars[(validChars.find(cipherText[j])+i+(index+1+validChars.find(cipherText[j-1])+32)*(j+2))%len(validChars)]   # Further conduct shifting using operation factors and the previous cipher character.
        temp = index            # Generate the operation factor temp from index.
        for j in range(4 + int(len(plainText)*1.1)):          # Exchange the position of two characters depending on operation factors.
            factorA = (temp**2+opralen*temp)%txtlen
            factorB = (temp+1 + ord(key[index]))%txtlen
            cipherText[factorA], cipherText[factorB]\
                 = cipherText[factorB], cipherText[factorA]
            temp += 1
    cipherText = "".join(cipherText)         # Convert the list to string
    return cipherText

def decryptRound(cipherText, key, validChars=' !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~'):       # Decrypt a given cipher text using a given key for one round
    if not cipherText: return ""
    for i in cipherText: assert i in validChars, f"Invalid character in ciphertext: {i}"
    plainText = list(cipherText)            # Initialize the plain text list
    opralen, txtlen = int(0.1*len(cipherText)), len(cipherText)
    for index, i in zip(range(len(key)-1,-1,-1), list(key)[::-1]):          # Generate the operation factor index and i from the given key in reverse order.
        i = ord(i)-32
        temp = index + 3 + int(len(plainText)*1.1)            # Generate the operation factor temp from index in reversing or.
        for j in range(4 + int(len(plainText)*1.1)):          # Exchange the position of two characters depending on operation factors.
            factorA = (temp**2+opralen*temp)%txtlen
            factorB = (temp+1 + ord(key[index]))%txtlen
            plainText[factorA], plainText[factorB]\
                 = plainText[factorB], plainText[factorA]
            temp -= 1
        for j in range(len(plainText)-1, -1, -1):
            plainText[j] = validChars[(validChars.find(plainText[j])-i-i//3-i//17-(index+1)*(j+2))%len(validChars)]            # Conduct reverse linear shifting using operation factors.
            if j:
                plainText[j] = validChars[(validChars.find(plainText[j])-i-(index+1+validChars.find(plainText[j-1])+32)*(j+2))%len(validChars)]         # Further conduct reverse shifting using operation factors and the previous cipher character.
    plainText = "".join(plainText)          # Convert the list to string
    return plainText

def encrypt(plainText, key):            # Encrypt the plain text using the given key for a certain amount of rounds, depending on the key.
    for i in plainText:                 # Check if the characters in the text and the key are supported.
        if ord(i) not in range(32, 127):
            raise ValueError("Invalid character "+i+" in plain text")
    for i in key:
        if ord(i) not in range(32, 127):
            raise ValueError("Invalid character "+i+" in key")
    temp = 0
    if plainText == "": return ""
    for i in key: temp += ord(i)        # Generate the number of rounds to be encrypted.
    cipherText = plainText
    for i in range(4 + temp%3):         # Encrypt the plain text for (4 + temp%3) rounds.
        cipherText = encryptRound(cipherText, key)
    return cipherText

def decrypt(cipherText, key, validChars=' !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~'):           # Decrypt the plain text using the given key for a certain amount of rounds, depending on the key.
    for i in cipherText:                # Check if the characters in the text and the key are supported.
        if ord(i) not in validChars:
            raise ValueError("Invalid character "+i+" in cipher text")
    for i in key:
        if ord(i) not in range(32, 127):
            raise ValueError("Invalid character "+i+" in key")
    temp = 0
    if cipherText == "": return ""
    for i in key: temp += ord(i)        # Generate the number of rounds to be decrypted.
    plainText = cipherText
    for i in range(4 + temp%3):         # Decrypt the plain text for (4 + temp%3) rounds.
        plainText = decryptRound(plainText, key)
    return plainText


