import zmq
import random
#import numpy as np
from nonNumpyPolynomial import *
from group import *
from modular_polynomial import *

#bit of the random generated secret
BITS_SECRET=256

# SOCKET
LOCAL_PORT = 4080
SERVER_HOST = "localhost"
SERVER_PORT = 4080
POLL_WAIT_TIME=1000



def random_polynomial(group, degree, y_intercept="random"):
    '''
    Create a random polynomial of the given degree over the group given. 
    It is possible to set the intercept.
    '''
    coefficients=[0]*(degree+1)
    if y_intercept=="random":
        coefficients[0]=int(group.rand_int())
    else:
        coefficients[0]=y_intercept
    for i in range(1,degree+1):
        coefficients[i]=int(group.rand_int())
    return nonNumpyPolynomial(coefficients)
    

def commitment_check(commitments, share, g1, threshold, group):
    '''
    Check the validity of the share given using the commitments according the Feldman protocol
    '''
    if threshold!=len(commitments): return False
    check=1
    for j in range(threshold):
        check=group.mul(check,group.pow(commitments[j],(share["index"]**j)))
    return (group.pow(g1,share["value"])==check)


def dealer(number_of_participant,threshold,master_secret=None):
    '''
    Feldman protocol on the delaer side.
    '''
    #Preparation step, connection to the socket, it is supposed to use a secure socket instead of a normal one.
    socket = zmq.Context().socket(zmq.REP)
    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)

    socket.bind(f"tcp://*:{LOCAL_PORT}")
    print("Connection initiated.")
    #Generate group Z_q
    group=PrimeGroup(gen_prime(num_bits=BITS_SECRET))

    #Generate the master secret if not given
    if master_secret==None :
        master_secret=group(random.randint(1,2**BITS_SECRET))

    #Step 1: sample a t (threshold-1) degree polynomial f(x)
    function_f=random_polynomial(group=group,degree=threshold-1,y_intercept=master_secret)


    #Step 2: create the shares for each participant
    shares=[None]*(number_of_participant+1)
    for i in range(1,number_of_participant+1):
        shares[i]={"index":i,"value":function_f(i)}

    #Step 3: compute the commitments
    commitments=[0]*(threshold)
    g1=group.find_generator()
    f_coefficients=function_f.get_coefficients()
    for i in range(threshold):
        commitments[i]=group.pow(g1,int(f_coefficients[i]))
        
    #Step 4: send the share (i,f(i)) to P_i and the commitments to everyone
    print("Sharing with the parties:")
    for i in range(1,number_of_participant+1):
        print(f"Waiting for party {i} of {number_of_participant}")
        while True:
            obj = dict(poller.poll(POLL_WAIT_TIME))
            if socket in obj and obj[socket] == zmq.POLLIN and socket.recv_pyobj():
                socket.send_pyobj([commitments,shares[i],group,g1])
                break

    socket.close()
    
def party(threshold):
    '''
    Pederson protocol on the party side. (Single party, n has to be executed.)
    '''
    print("Waiting for the dealer.")

    #Preparation step, connection to the socket, it is supposed to use a secure socket instead of a normal one.
    socket = zmq.Context().socket(zmq.REQ)
    socket.connect(f"tcp://{SERVER_HOST}:{SERVER_PORT}")
    socket.send_pyobj(True)
    print("Connected to the dealer, waiting for the share and the commit.")

    #Step 4: receive the share and the commit
    [commitments,share,group,g1]=socket.recv_pyobj()
    socket.close()

    #Check the validity of the share through the commit
    if commitment_check(commitments, share, g1, threshold, group):
        print(f"Confirmed the share through the commitment, the value is: ( {share["index"]} : {share["value"]})")
    else:
        print(f"Confirmation failed: the share don't match the commitment.\nShare:\n( {share["index"]} : {share["value"]})\n\nthreshold:\n{threshold}\n\npi_shares:\n{commitments}\n\ng:\n{g1}\n\nprime:\n{group.getPrime()}")


#Command line parsing implementation
    # -d :      Take the role of dealer for this run of the protocol.
    # -t int :  The number of participant needed to reconstruct the secret. (default=majority)
    # -n int :  The number of share to be issued.

if __name__ == '__main__':
    import argparse

    def init():
        parser = argparse.ArgumentParser(description="Run Pederson shared secret protocol.")
        parser.add_argument('-d',
                            '--isDealer',
                            action='store_true',
                            help="Take the role of dealer for this run of the protocol."
                            )
        parser.add_argument(
            "-t",
            "--threshold",
            default="majority",
            help=("The number of participant needed to reconstruct the secret (default=majority)"),
        )
        parser.add_argument(
            "-n",
            "--participants",
            default=3,
            help="The number of share to be issued")
        
        parser.add_argument(
            "-mp",
            "--multiple_participants",
            default=1,
            help="Run the party protocol for multiple participants")

        isDealer=parser.parse_args().isDealer
        threshold=parser.parse_args().threshold
        number_of_participant=int(parser.parse_args().participants)
        multiple_participants=int(parser.parse_args().multiple_participants)
        if threshold=="majority":
            #half by defect plus one
            threshold=number_of_participant//2 +1
        else:
            threshold=int(threshold)

        if isDealer:
            dealer(
                number_of_participant=number_of_participant,
                threshold=threshold
            )
        else:
            for i in range(multiple_participants):
                party(threshold)

    init()
