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
LOGR    = HOME + "switcher.log"
FMT1    = "%(asctime)s %(message)s"     # Format for logging: template
FMT2    = "%m/%d/%Y %H:%M:%S"           # Format for logging: date/time
WURL    = ""                            # WITNESS PROPOSAL URL
ACNT    = ""                            # WITNESS ACCOUNT NAME HERE
PASS    = ""                            # WALLET PASSWORD FOR SQLite WALLET
PKEY    = ""                            # PRIVATE ACTV KEY FOR WITNESS ACCOUNT
FREQ    = 30                            # Missed block sample time in seconds
FLIP    = 3                             # Threshold of missed blocks to switch
RSET    = 240                           # Reset after this many good samples
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
                 "BTS3..."
    ]

# Setup the API instance we'll use
API = BitShares(API_NODES, nobroadcast=False)
# set_shared_bitshares_instance(API)       # Not sure what this could be for

####################################################
# End of constants and global variable definitions #
####################################################

# Check how many blocks have been missed and switch signing keys if required
def checkWitness(startMisses, loopCounter, counterOnLastMiss, previousMisses,
                 nextKey):

    status = Witness(ACNT)
    currentKey = status['signing_key']
    missed = status['total_missed']

    print("\r%d samples, missed=%d(%d), key=%.16s..." %
        (loopCounter, missed, counterOnLastMiss, currentKey), end='')

    if startMisses == -1:
        startMisses = previousMisses = missed
        counterOnLastMiss = loopCounter

    if missed > previousMisses:
        counterOnLastMiss = loopCounter
        delta = previousMisses - startMisses
        msg = "\nMissed another block! (delta=%d)" % delta
        print(msg)
        logging.info(msg)
        previousMisses = missed
        if delta >= FLIP:
            # Flip witness to backup
            key = WITNESS_KEYS[nextKey]
            msg = "Time to switch! (next key: %s)" % key
            print(msg)
            logging.info(msg)
            API.wallet.unlock(walletpwd)
            API.update_witness(witness, url=witnessurl, key=key)
            time.sleep(6) # Wait 2 block times before trying to confirm switch

            status = Witness(ACNT)
            if currentKey != status['signing_key']:
                currentKey = status['signing_key']
                msg = "Witness updated. Now using " + currentKey
                print(msg)
                logging.info(msg)
                startMisses = -1  # Starting fresh, reset counters
                nextKey = (nextKey + 1) % len(WITNESS_KEYS)
            else:
                msg = "Signing key did not change! Will try again in " 
                msg += FREQ + " seconds"
                print(msg)
                logging.info(msg)
    else:
        # If we haven’t missed any for awhile reset the counters
        if loopCounter - counterOnLastMiss >= RSET:
            startMisses = -1

    return (startMisses,loopCounter,counterOnLastMiss,previousMisses,nextKey)


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
        print("Enter it again to verify.")
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
            prompt = "Create a new wallet with the password you entered (y/n)?"
            if input(prompt) == 'y':
                 print("\nSorry, no way currently to remove old wallet state.")
                 print("You will need to manage the wallet externally.")
                 print("Alternatively you can delete %s and run this again." % WLET)
#                API.wallet.wipe()  # New in dev branch, but may not work here
                 exit(-1)  # Remove when wipe() removes 'wallet exists' state
            else:
                print("Ok, sorry it didn't work out. Bye!")
                exit(-1)

    if not API.wallet.created():  # This should also eval true if wiped above
        try:
            print("No wallet exists! Creating one now...")
            API.wallet.newWallet(pw)
            API.wallet.unlock(pw)
            prompt = "Please enter the private key for your witness account"
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
        name = input("Please enter your witness account name: ")
        try:
            account = Account(name)
        except: # This will NOT CATCH AccountDoesNotExistsException
            print("That isn't a valid account!")
        else:
            if not account.is_ltm:
                print("That doesn't appear to be a witness account!")
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

    # Update these if user didn't define in constants
    PASS  = credentials['PASS']     # Wallet password
    PKEY  = credentials['PKEY']     # Witness private key
    ACNT  = getWitnessAccountName(ACNT)  # Can't get from private key in wallet

    # Set nextKey index based on signing key in use right now
    status = Witness(ACNT)
    for key in range(len(WITNESS_KEYS)):
        if status['signing_key'] == WITNESS_KEYS[key]:
            nextKey = key

    startMisses = -1 # Set to -1 to reset / init
    previousMisses = status['total_missed']
    loopCounter = counterOnLastMiss = 0    # Initialize counters

    logging.info("Starting missed block monitoring for " + ACNT)
    while True:
        checkWitness(startMisses, loopCounter, counterOnLastMiss,
                     previousMisses, nextKey)
        sys.stdout.flush()
        loopCounter += 1
        time.sleep(FREQ)

