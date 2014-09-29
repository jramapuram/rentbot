__author__ = 'jason'

import imaplib
import re
import email
import time
from treelib import Tree
from os import path
import xml.etree.ElementTree as ET
from DataBaseLoader import DataBaseLoader

#member variables
db_file_location = "./db"
tree_location = "./rent.xml"

def login_user(user_name, imap_server, pwd):
    mail = imaplib.IMAP4_SSL(imap_server)
    mail.login(user_name, pwd)
    mail.select("inbox")
    return mail

def parse_xml(path):
    tree = ET.parse(path)
    bill_list = []

    # eg:       (cox, "Do_Not_Reply_Prod@cox.com")                  (rent, 2000)
    #          /                                 \            &    /            \
    #      (Evan, 0.5)                        (Jason, 0.5)       (Evan, 0.45)   (Jason, 0.55)
    for bill in tree.findall("bill"):
        billname = bill.get("name")
        bill_tree = Tree()

        bill_value = bill.get("fixed")
        if bill_value is None:
            bill_value = bill.get("from_email")
        bill_tree.create_node(tag=billname, identifier=billname, data=bill_value)

        for user in bill.findall("user"):
            username = user.get("name")
            ratio = user.get("ratio")
            bill_tree.create_node(tag=username, identifier=username, parent=billname, data=ratio)
        bill_list.append(bill_tree)

    for bt in bill_list:
        print bt.to_json(with_data=True)

    return bill_list

# note that if you want to get text content (body) and the email contains
# multiple payloads (plaintext/ html), you must parse each message separately.
# use something like the following: (taken from a stackoverflow post)
def get_first_text_block(email_message_instance):
    maintype = email_message_instance.get_content_maintype()
    if maintype == 'multipart':
        for part in email_message_instance.get_payload():
            if part.get_content_maintype() == 'text':
                return part.get_payload()
    elif maintype == 'text':
        return email_message_instance.get_payload()

def parse_amount(imap_object, from_user, regex):
    print 'from=', from_user
    date_str = time.strftime("01-%b-%Y")
    result, data = imap_object.search(None, '(FROM "%s" SENTSINCE "%s")' % (from_user, date_str))
    ids = data[0]
    id_list = ids.split()
    print "There are", len(id_list), "emails matching this category for this month"

    # if len(id_list) > 0:
    #     latest_email_uid = data[0].split()[-1]
    #     result, data = imap_object.uid('fetch', latest_email_uid, '(RFC822)')
    #     email_msg = email.message_from_string(data[0][1])
    #     for msg in email_msg.items():
    #         print get_first_text_block(msg)
        #print re.search(regex, data[0]).groupdict()
    #todo: get raw text & regex as '\s+\d+\\.\d*\s+'

# main
db_pwd = None
if path.isdir(db_file_location):
    db_pwd = raw_input("Please enter db password to continue: ")
dbl = DataBaseLoader(db_file_location, db_pwd)
user_db = dbl.load()

#parse xml file
bill_list = parse_xml(tree_location)

# now create imap objects & query it
for k, v in user_db.items():
    user_data = k.split('#')
    assert len(user_data) == 2
    current_user = login_user(user_data[0], user_data[1], v)
    for bill in bill_list:  # per bill
        for node in bill.subtree(bill.root).expand_tree(mode=Tree.DEPTH):
            if '@' in bill[node].data:
                parse_amount(current_user, bill[node].data, "\s+\d+\.\d*\s+")
