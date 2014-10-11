__author__ = 'jason'

import os.path
import bcrypt
import leveldb
import sys
from simplecrypt import encrypt, decrypt


class DatabaseLoader:

    # helper to parse out the db
    def load_database(self, file_path, db_pwd):
        db = leveldb.LevelDB(file_path)
        db_kv_set = {}
        encrypted_db_pwd = db.Get('password')

        if bcrypt.hashpw(db_pwd, encrypted_db_pwd) == encrypted_db_pwd:
            for k, v in db.RangeIter():
                if k != 'password':
                    db_kv_set[k] = decrypt(db_pwd, v)
        else:
            print 'Error, invalid DB pwd!'
        return db_kv_set

    def load(self):
        data_map = {}
        if os.path.isdir(self.db_file_location):
            data_map = self.load_database(self.db_file_location, self.db_pwd)
        else:
            # Get our users and toss them into a set to cleanup dupes
            available_users = []
            is_email_reqd = False
            for bill in self.bill_list:
                if '@' in bill[bill.root].data:  # Check to see if we require emails
                    is_email_reqd = True
                for node in bill.children(bill.root):
                    available_users.append(node.identifier)
            available_users = set(available_users)

            if is_email_reqd:
                print 'Setting up rentbot for first run...'
                for user in available_users:
                    if raw_input("Would you like to use %s\'s email to pull bills?" % user).lower().strip() == "yes":
                        current_user = raw_input("Enter %s\'s email address :" % user)
                        imap_server = raw_input("Enter %s\'s imap server :" % user)
                        smtp_server = ""
                        if self.dest.lower().strip() == "email":
                            smtp_server = raw_input("Enter %s\'s smtp server:" % user)
                        current_pwd = raw_input("Enter %s\'s password :" % user)
                        data_map['%s#%s' % (current_user, imap_server)] = current_pwd  # XXX
                        data_map['%s|%s' % (current_user, smtp_server)] = current_pwd  # XXX
                    else:
                        print "I\'m assuming that was a no.."

            # Some minimal checking
            if is_email_reqd and len(data_map) > 0:
                # save all the values we now have
                self.db_pwd = raw_input("Enter a master password to encrypt the database: ")
                ldb = leveldb.LevelDB(self.db_file_location)
                ldb.Put('password', bcrypt.hashpw(self.db_pwd, bcrypt.gensalt()))
                for k, v in data_map.iteritems():
                    ldb.Put(k, encrypt(self.db_pwd, v))
            elif is_email_reqd:
                print "XML file states that some data is to be parsed from email."
                print "Please re-run the program & enter at LEAST 1 email (or) don't use an email topology"
                sys.exit(-1)  # XXX

        return data_map

    def __init__(self, bill_list, db_file_location, db_pwd, dest):
        self.db_file_location = db_file_location
        self.bill_list = bill_list
        self.db_pwd = db_pwd
        self.dest = dest