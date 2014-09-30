__author__ = 'jason'

import imaplib
import re
import time
from treelib import Tree
from os import path
import xml.etree.ElementTree as ET
from DatabaseLoader import DatabaseLoader

#member variables
db_file_location = "./db"
tree_location = "./rent.xml"

#returns a logged in imap object with the inbox folder selected
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

def parse_amount(imap_object, from_user, regex):
    date_str = time.strftime("01-%b-%Y")
    result, data = imap_object.uid('search', None, '(FROM "%s" SENTSINCE "%s")' % (from_user, date_str))

    emails = data[0].split()
    print 'There are %d emails in the timeframe since %s which are from = %s.' % (len(emails), date_str, from_user)
    for email in emails:
        result, data = imap_object.uid('fetch', email, '(RFC822)')
        return re.findall(regex, data[0][-1])
        #print data[0][-1] #uncomment to get raw email

def parse_emails(user_db, bill_list):
    for k, v in user_db.items():
        user_data = k.split('#')
        assert len(user_data) == 2  # eg:'name#email', TODO: have option to not require everyone's email
        current_user = login_user(user_data[0], user_data[1], v)
        for bill in bill_list:  # per bill
            for node in bill.subtree(bill.root).expand_tree(mode=Tree.DEPTH):
                if '@' in bill[node].data:
                    print parse_amount(current_user, bill[node].data, "\$\s*\d+\.\d*")

def get_db(bill_list):
    db_pwd = None
    if path.isdir(db_file_location):
        db_pwd = raw_input("Please enter db password to continue: ")
    dbl = DatabaseLoader(bill_list, db_file_location, db_pwd)
    user_db = dbl.load()
    return user_db


if __name__ == '__main__':
    #parse xml file, TODO: use this in the data parsing
    bill_list = parse_xml(tree_location)

    #get a handle to our database
    user_db = get_db(bill_list)

    # now create imap objects & query it
    parse_emails(user_db, bill_list)
