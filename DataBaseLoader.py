__author__ = 'jason'

import os.path
import bcrypt
import leveldb
from simplecrypt import encrypt, decrypt


class DataBaseLoader:

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

    #TODO : implement this method to save to an xml file
    # def parse_cli(self):
    #     num_bills = int(raw_input('Enter the number of bills:'))
    #     self.data_map['num_bills'] = num_bills
    #
    #     # get all the bill ratios
    #     for j in xrange(num_bills):
    #         bill_name = raw_input("Enter bill #%d name :" % j)
    #         for user in users:
    #             current_pwd = raw_input("Enter bill ratio for user %s :" % user)
    #             self.data_map['user2jr_%s' % current_user] = current_pwd

    def load(self):
        data_map = {}
        if os.path.isdir(self.db_file_location):
            data_map = self.load_database(self.db_file_location, self.db_pwd)
        else:
            print 'Setting up rentbot for first run...'
            num_users = int(raw_input('Enter the number of users:'))

            # get all users and setup their login info into db
            for i in xrange(num_users):  # TODO: change to stop input using null statement
                current_user = raw_input("Enter user #%d's email :" % i)
                imap_server = raw_input("Enter imap server for %s :" % current_user)
                current_pwd = raw_input("Enter password for user %s :" % current_user)
                data_map['%s#%s' % (current_user, imap_server)] = current_pwd

            # save all the values we now have
            self.db_pwd = raw_input("Enter a password to encrypt the database: ")
            ldb = leveldb.LevelDB(self.db_file_location)
            ldb.Put('password', bcrypt.hashpw(self.db_pwd, bcrypt.gensalt()))
            for k, v in data_map.iteritems():
                ldb.Put(k, encrypt(self.db_pwd, v))

        return data_map

    def __init__(self, db_file_location, db_pwd):
        self.db_file_location = db_file_location
        self.db_pwd = db_pwd