__author__ = 'jason'

import imaplib
import re
import sys
import getpass
import smtplib
import time
from treelib import Tree
from os import path
from collections import defaultdict
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
    destination = "console"

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

    # Get the location to dump our results
    for d in tree.findall("output"):
        destination = d.get("destination")

    return (bill_list, destination)

def parse_amount_email(imap_object, from_user, regex):
    date_str = time.strftime("01-%b-%Y")
    result, data = imap_object.uid('search', None, '(FROM "%s" SENTSINCE "%s")' % (from_user, date_str))

    emails = data[0].split()
    #print 'There are %d emails in the timeframe since %s which are from = %s.' % (len(emails), date_str, from_user)
    for email in emails:
        result, data = imap_object.uid('fetch', email, '(RFC822)')
        return re.findall(regex, data[0][-1])
        #print data[0][-1] #uncomment to get raw email

def parse_emails(user_db, bill_list):
    for k, v in user_db.items():
        if '#' in k:  # XXX
            user_data = k.split('#')
            assert len(user_data) == 2  # eg:'name#email'
            current_user = login_user(user_data[0], user_data[1], v)
            for bill in bill_list:  # per bill
                for node in bill.subtree(bill.root).expand_tree(mode=Tree.DEPTH):
                    if '@' in bill[node].data:
                        value_list = parse_amount_email(current_user, bill[node].data, "\$\s*(\d+\.\d*)")
                        total_amount = 0.0
                        for bill_amount in value_list:
                            total_amount += float(bill_amount)
                        bill[node].data = str(total_amount)

def get_db(bill_list, dest):
    db_pwd = None
    if path.isdir(db_file_location):
        db_pwd = getpass.getpass("Please enter db password to continue: ")
    dbl = DatabaseLoader(bill_list, db_file_location, db_pwd, dest)
    user_db = dbl.load()
    return user_db

def parse_payments(bill_list):
    for bill in bill_list:
        # at this point we assume that we have replaced emails with values
        if bill[bill.root].data is not None and '@' in bill[bill.root].data:
            print "Error : Could not fill in data for %s bill from email %s" % (bill[bill.root].identifier, bill[bill.root].data)
            sys.exit(-3)  # XXX
        amount = float(bill[bill.root].data)

        #multiply out our rations
        for node in bill.children(bill.root):
            node.data = str(float(node.data) * amount)

def send_email(data_blob, to_email, port, user_db):
     for k, v in user_db.items():
        if '|' in k:  # XXX
            user_data = k.split('|')
            assert len(user_data) == 2  # eg:'name|server'

            #create smtp object
            server = smtplib.SMTP(user_data[1], port)
            server.starttls()
            server.login(user_data[0], v)

            #now send away!
            server.sendmail("rentbot@localhost", to_email, data_blob)

if __name__ == '__main__':
    print'                       __ ___.           __'
    print'_______   ____   _____/  |\_ |__   _____/  |_'
    print'\_  __ \_/ __ \ /    \   __\ __ \ /  _ \   __\\'
    print' |  | \/\  ___/|   |  \  | | \_\ (  <_> )  |  '
    print' |__|    \___  >___|  /__| |___  /\____/|__|  '
    print'             \/     \/         \/             '
    print'version 0.01'
    print' '

    #parse xml file
    (bill_list, dest) = parse_xml(tree_location)

    #get a handle to our database
    user_db = get_db(bill_list, dest)

    # query email for the required amounts
    for key in user_db.keys():
        if '#' in key:  # XXX
            parse_emails(user_db, bill_list)
            break

    # tabulate all values
    parse_payments(bill_list)

    # format our print statement
    output_str = ""
    bill_totals = defaultdict(lambda: 0)
    for bill in bill_list:
        for node in bill.children(bill.root):
            output_str += "{0:20} owes $ {1:7} for {2:20}".format(node.identifier, node.data, bill.root) + "\n"
            bill_totals[node.identifier] += float(node.data)

    output_str += "\n\nGrand Totals:\n"
    for k,v in bill_totals.iteritems():
        output_str += k + " : " + str(v) + "\n"

    if dest.lower().strip() == "console":
        print output_str
    else:
        # TODO : iterate through users
        send_email(output_str, "jason@ramapuram.net", 587, user_db)
