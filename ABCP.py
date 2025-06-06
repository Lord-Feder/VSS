import zmq
import random
from hashlib import sha256
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
    

def commitment_check(i, commit_b, commit_f, share, y, function_r, group):
    '''
    Check the validity of the share given using the pi_share according the ABCP protocol
    '''
    commit_digest = digest_of_commitments(group, b=commit_b, f=commit_f)

    compare_b=sha256((str(function_r(i)+commit_digest*share)+str(y[0])).encode()).hexdigest()
    compare_f=sha256((str(share)+str(y[1])).encode()).hexdigest()
    return compare_b==commit_b[i] and compare_f==commit_f[i]



def digest_of_commitments(group, b, f):
    return group(int(sha256(str("".join(b)+"".join(f)).encode()).hexdigest(),16))

def dealer(number_of_participant,threshold,master_secret=None):
    '''
    ABCP protocol on the delaer side.
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

    #Step 1: sample two t (threshold-1) degree polynomial f(x), b(x).two random values for each participant
    function_f=random_polynomial(group=group,degree=threshold-1,y_intercept=master_secret)
    function_b=random_polynomial(group=group,degree=threshold-1)

    #Step 2: generate two random values for each participant
    y=[[0,0]]*(number_of_participant+1)
    for i in range(1,number_of_participant+1):
        y[i]=[int(group.rand_int()),int(group.rand_int())]


    #Step 3: compute the commitment c_i = Commit(f(i),y_i) and c'_i = Commit(b(i),y'_i)
    commit_b=[""]*(number_of_participant+1)
    commit_f=[""]*(number_of_participant+1)

    for i in range(1,number_of_participant+1):
        commit_b[i]= sha256((str(function_b(i))+str(y[i][0])).encode()).hexdigest()
        commit_f[i]= sha256((str(function_f(i))+str(y[i][1])).encode()).hexdigest()


    #Step 4: create a digest out of the commits (d)
    commit_digest = digest_of_commitments(group, b=commit_b, f=commit_f)

    
    #Step 5: produce r(x) = b(x) - d*f(x)
    f_coefficients=function_f.get_coefficients()
    b_coefficients=function_b.get_coefficients()

    function_r= nonNumpyPolynomial([b_coefficients[i] - commit_digest*f_coefficients[i] for i in range(threshold)])
    

    #Step 6: send the share to the corresponding party with the y_i, y'_i and broadcast the commitments 
    shares=[None]*(number_of_participant+1)
    for i in range(1,number_of_participant+1):
        shares[i]=int(function_f(i))

    print("Sharing with the parties:")
    for i in range(1,number_of_participant+1):
        print(f"Waiting for party {i} of {number_of_participant}")
        while True:
            obj = dict(poller.poll(POLL_WAIT_TIME))
            if socket in obj and obj[socket] == zmq.POLLIN and socket.recv_pyobj():
                socket.send_pyobj([commit_b,commit_f,i,function_r,shares[i],group,y[i]])
                break

    socket.close()

   
def party():
    '''
    Pederson protocol on the party side. (Single party, n has to be executed.)
    '''
    print("Waiting for the dealer.")

    #Preparation step, connection to the socket, it is supposed to use a secure socket instead of a normal one.
    socket = zmq.Context().socket(zmq.REQ)
    socket.connect(f"tcp://{SERVER_HOST}:{SERVER_PORT}")
    socket.send_pyobj(True)
    print("Connected to the dealer, waiting for the share and the commit.")

    #Step 6: receive the share and the commit
    [commit_b,commit_f,i,function_r,share,group,y]=socket.recv_pyobj()
    socket.close()

    #Check the validity of the share through the commit
    if commitment_check(i, commit_b, commit_f, share, y, function_r, group):
        print(f"Confirmed the share through the commitment, the value is: ( {i} : {share})")
    else:
        print(f"Confirmation failed: the share don't match the commitment.\nShare:\n( {i} : {share})\n\ncommitment on b function:\n{commit_b}\n\ncommitment on f function:\n{commit_f}\n\ny1,y2:\n{y[0]},{y[1]}\n\nprime:\n{group.getPrime()}\n\nfunction r:")
        coef_r=function_r.get_coefficients()
        str_r=str(coef_r[0])
        for i in range(len(1,coef_r)):
            str_r+= f" + {coef_r[i]}*x^{i}"
        print(str_r)



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
                party()

    init()
