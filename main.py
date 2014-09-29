__author__ = 'jason'

import imaplib
import email
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

    # eg: (cox) -> (Evan) -> (0.5)
    for bill in tree.findall("bill"):
        billname = bill.get("name")
        bill_tree = Tree()

        bill_value = bill.get("fixed")
        if bill_value == None:
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

# main
db_pwd = None
if path.isdir(db_file_location):
    db_pwd = raw_input("Please enter db password to continue: ")
dbl = DataBaseLoader(db_file_location, db_pwd)
user_db = dbl.load()
db_pwd = None

#parse xml file
bill_list = parse_xml(tree_location)

# now create imap objects & query it
for k, v in user_db.items():
    user_data = k.split('#')
    assert len(user_data) == 2
    current_user = login_user(user_data[0], user_data[1], v)

