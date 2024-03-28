import sys
import os
import time

#a couter with external variable should be implemented to sum all the restarting

def restart (numb_rest):
    print(sys.argv)
    print (sys.executable)
    print ("restarting")
    if numb_rest == 1 :
        sys.exit() #stop the loop 
        print("hey")
    else :
        os.execv(sys.executable,["python"] + sys.argv)

a = [1,2,3,4,5,6,7,8,9,0]

try: 
    for val in a:
        print (1/val)
        time.sleep(1)

except:
    numb_rest = 1
    restart(numb_rest)
    