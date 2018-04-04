#!/usr/bin/env python3
#
# This script is based on roelandp's witness monitor that
# broadcasts an update_witness msg when the number of missed
# blocks excede the value defined by the FLIP constant.
#
import sys
import time
import logging
from getpass import getpass
from bitshares import BitShares
from bitshares.account import Account
from bitshares.witness import Witness
#from bitshares.instance import set_shared_bitshares_instance # ???

# Constants (User will be prompted for ACNT, PASS and PKEY if left empty)
HOME    = "/home/<account>/"            # CHANGE TO ACCOUNT THIS RUNS UNDER
WLET    = HOME + ".local/share/bitshares/bitshares.sqlite"
LOGR    = HOME + "switcher.log"         # LOCATION OF LOG FILES
FMT1    = "%(asctime)s %(message)s"     # Format for logging: template
FMT2    = "%m/%d/%Y %H:%M:%S"           # Format for logging: date/time
WURL    = ""                            # WITNESS PROPOSAL URL
ACNT    = ""                            # WITNESS ACCOUNT NAME HERE
PASS    = ""                            # WALLET PASSWORD FOR SQLite WALLET
PKEY    = ""                            # PRIVATE ACTV KEY FOR WITNESS ACCOUNT
FREQ    = 30                            # Missed block sample time in seconds
FLIP    = 3                             # Threshold of missed blocks to switch
RSET    = 120                           # Reset after this many unmissed bloks
LEVL    = logging.INFO                  # Set 2 logging.DEBUG for lots of data

API_NODES   = [                         # API server node list
    "wss://bts.proxyhosts.info/wss",    # BitShares load balanced nodes
    "wss://nohistory.proxyhosts.info/wss" # Load balanced without history
#    "wss://api.bts.blckchnd.com"        # location: "Falkenstein, Germany"
#    "wss://dex.rnglab.org",             # location: "Netherlands"
#    "wss://dexnode.net/ws",             # location: "Dallas, USA"
#    "wss://kc-us-dex.xeldal.com/ws",    # location: "Kansas City, USA"
#    "wss://la.dexnode.net/ws"           # location: "Los Angeles, USA"
    ]

# Array of alternative witness signing keys we'll switch to upon failure
WITNESS_KEYS = [ "BTS1...",
                 "BTS2...",
                 "BTS3..." ]

# Setup the API instance we'll use
API = BitShares(API_NODES, nobroadcast=False)
# set_shared_bitshares_instance(API)       # Not sure what this could be for

global startMisses, nextIdx, previousMisses, loopCounter, counterOnLastMiss
##############################################################################
#              End of constants and global variable definitions              #
##############################################################################

# Check how many blocks have been missed and switch signing keys if required
#
# There is no explicit facility in Python for true local static variables.
# All methods require a prefix or greater indentation if a class structure
# is used. However the only way to fully protect and encapsulate variables
# is within a class.  I  am using globals mainly to avoid the ugliness and
# to simplify the initialization, as well as bringing all of it except the
# the following line back within this function.
startMisses = -1
def checkWitness():
    # Define and initialize the "static" variables we need to persist
    global startMisses,nextIdx,previousMisses,loopCounter,counterOnLastMiss

    status = Witness(ACNT)
    missed = status['total_missed']
    currentKey = status['signing_key']

    # Monitoring a fresh witness, so reset all "static" variables
    if startMisses == -1:
        startMisses = previousMisses = missed
        counterOnLastMiss = loopCounter = 0
        keyCount = len(WITNESS_KEYS)
        for k in range(keyCount):
            if currentKey == WITNESS_KEYS[k]:
                nextIdx = (k + 1) % keyCount

    print("\r%d samples, missed=%d(%d), key=%.16s..." %
        (loopCounter, missed, counterOnLastMiss, currentKey), end='')

    if missed > previousMisses:
        if previousMisses != -1:    # Switch failure?
            counterOnLastMiss = loopCounter     # No.
            delta = previousMisses - startMisses
            previousMisses = misses
            msg = "Missed another block! (delta=%d)" % delta
            print("\n", msg)
            logging.info(msg)
        else:
            msg = "Rebroadcasting switch to (%s)..." % key
            print("\n", msg)
            logging.info(msg)

        if delta >= FLIP:
            key = WITNESS_KEYS[nextIdx]
            if previousMisses != -1:
                msg = "Time to switch! (next key: %s)" % key
                print("\n", msg)
                logging.info(msg)
            # Flip witness to a backup
            API.wallet.unlock(PASS)
            API.update_witness(ACNT, url=WURL, key=key)
            time.sleep(9) # Wait 3 block times before trying to confirm switch

            if Witness(ACNT)['signing_key'] == key:
                msg = "Witness updated. Now using " + key
                print("\n", msg)
                logging.info(msg)
                startMisses = -1    # Starting fresh, reset all counters
            else:
                msg = "Signing key did not change! Will try again in "
                msg += str(FREQ) + " seconds"
                previousMisses = -1 # This will flag a retry
                print("\n", msg)
                logging.info(msg)
    else:
        # If we haven’t missed any for awhile reset the counters
        if loopCounter - counterOnLastMiss >= RSET:
            startMisses = -1

    loopCounter += 1



#
#  W a l l e t     I n i t i a l i z a t i o n
#

# Get sensitive input such as password or private key from user.
# Doesn't return until both inputs match or ^C / abort.
def get_secret_input(prompt):
    secret = ""
    while not secret:
        print(prompt)
        in1 = getpass()
        print("Enter it again to verify> ")
        in2 = getpass()
        if in1 == in2:
            secret = in1
            print("Now add it to the code to avoid future prompting.\n")
            return secret
        else: print("Your inputs don't match! Try again...")


# First time run - initialize / open the wallet
def openWallet(credentials):
    pw     = credentials['PASS']
    pKey   = credentials['PKEY']

    # Get a wallet password from user if it isn't defined in Constants
    if not pw:
        pw = get_secret_input("Please enter your wallet password")
        credentials['PASS'] = pw

    if API.wallet.created():
        try:
            API.wallet.unlock(pw)
        except:
            print("A wallet exists but the password won't unlock it.")
            prompt= "Create a new wallet with the password provided (y/n)?> "
            if input(prompt).lower() == 'y':
                 doit = input("Are you REALLY sure?> ") # Get confirmation 1st
                 if doit.lower() == 'y':
                     # TODO: Make a backup of old wallet before wiping
                     try:
                         API.wallet.wipe(sure=True)
                     except:
                         print("\nAn error occurred removing the old wallet.")
                         print("You can delete %s and rerun this, or" % WLET)
                         print("manage the wallet manually & externally")
                         exit(-1)
            else:
                print("Ok, sorry it didn't work out. Bye!")
                exit(-1)

    if not API.wallet.created():  # This should also eval true if wiped above
        try:
            print("No wallet exists! Creating one now...")
            API.wallet.newWallet(pw)
            API.wallet.unlock(pw)
            prompt = "Please enter the private key for your witness account> "
            if not pKey:
                pKey = get_secret_input(prompt)
                credentials['PKEY'] = pKey
            API.wallet.addPrivateKey(pKey)
        except:
            print("A problem occured opening the wallet.")
            exit(-2)

    return(credentials)



# Get witness account name if not defined above in constants
def getWitnessAccountName(name):
    while not name:
        name = input("Please enter your witness account name> ").lower()
        try:
            account = Account(name)
        except: # TODO: Fix so this catches AccountDoesNotExistsException
            print("That isn't a valid account!")
        else:
            if not account.is_ltm:
                print("That is not a witness account!")
                name = ""
    return name

#
# Main entry point
#
if __name__ == "__main__":

    logging.basicConfig(filename=LOGR, level=LEVL, format=FMT1, datefmt=FMT2)

    # Open the wallet. Prompt for password and private key as required,
    #  if user didn't add them to the constants defined above.
    credentials = openWallet( {'PASS':PASS, 'PKEY':PKEY} )

    # Update these if user didn't define them in constants
    PASS  = credentials['PASS']         # Wallet password
    PKEY  = credentials['PKEY']         # Witness private key
    ACNT  = getWitnessAccountName(ACNT) # Can't get from private key in wallet

    logging.info("Starting missed block monitoring for " + ACNT)
    while True:
        checkWitness()
#       logging.info("nK=%d sM=%d colm=%d pM%d lC=%d" %
#           (nextKey,startMisses,counterOnLastMiss,previousMisses,loopCounter))
        sys.stdout.flush()
        time.sleep(FREQ)
