import unittest
import os
import sys
import time
import argparse
from epics import PV

#The format for the tests is: name, test type, first PV, second PV, write value, expected value

#Test types:
#   PUTGET = write a value to the first PV and then read the second PV to see if the value is the same
#   PUTERROR = write a  value to the first PV which should fail
#   EQUAL = compare the two PV values
#   GET = get the value of the second PV and check it matches the expected value

#Example test file:
#AFG3022B
#STATUS, PUTGET, OUTPUT1:STATUS:SP, OUTPUT1:STATUS, ON, ON 
#FUNC_SIN, PUTGET, OUTPUT1:FUNC:SP, OUTPUT1:FUNC, SIN, SIN
#FUNC_SQU, PUTGET, OUTPUT1:FUNC:SP, OUTPUT1:FUNC, SQU, SQU        
#FUNC_INVALID, PUTERROR, OUTPUT1:FUNC:SP, , JUNK, 
#STATUS_EQUAL, EQUAL, OUTPUT1:STATUS:SP, OUTPUT1:STATUS, , 


class TestSequence(unittest.TestCase):
    #Empty now, but at run time will be populated with our tests
    pass

def test_generator(iocname, type, pv_write, pv_read, value, expected):
    def test(self):
        pv_w = PV(iocname + pv_write)
        pv_r = PV(iocname + pv_read)
        if type == "PUTGET":
            pv_w.put(value)
            time.sleep(DELAY)
            got = pv_r.get(as_string=True)
            fail_string = 'The PV values do not match, sent %s got %s but expected %s' % (value, got, expected)
            self.assertEqual(expected, got, fail_string)
        elif type == "PUTERROR":
            self.assertRaises(ValueError, pv_w.put, value)
        elif type == "GET":
            as_str=False
            dbl = 0
            try:
                dbl = float(expected)
            except:
                as_str=True
                dbl = expected
            got = pv_r.get(as_string=as_str)
            fail_string = 'The value read was not as expected, got %s but expected %s' % (got, dbl)
            self.assertEqual(dbl, got, fail_string)
        elif type == "EQUAL":
            got1 = pv_r.get(as_string=True)
            got2 = pv_w.get(as_string=True)
            fail_string = 'The PV values do not match, got %s and %s' % (got1, got2)
            self.assertEqual(got1, got2, fail_string)
    return test
    
def read_tests(filename):
    ioc = ""
    tests = []
    
    firstline = True
    f = open(filename)
    for line in f:
        if firstline:
            #First line is the IOC name
            ioc = line.strip()
            firstline = False
        elif line.strip().startswith('#'):
            # skip line processing if first character is comment
            pass
        elif line.strip() != '':
            #It is a test
            #Name, type, write PV, read PV, write val, expected val
            temp = line.split(',')
            test = []
            for v in temp:
                test.append(v.strip())
            tests.append(test)           
    f.close()
    return (ioc, tests)    

if __name__ == '__main__': 
    #Defaults
    DELAY = 2
    filename = 'pv_tests.txt'
    results_dir = os.path.join(os.getcwd(), 'results')
    try:
        pvprefix = os.environ['MYPVPREFIX']
    except KeyError:
        pvprefix = ''
    
    #Parse the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--prefix',  nargs=1, help='The prefix for the IOC name (case-sensitive)')
    parser.add_argument('-d', '--dir',  nargs=1, help='The directory to write results to')
    args = parser.parse_args()
    
    if not args.prefix is None:
        pvprefix = args.prefix[0]
        
    if not args.dir is None:
        results_dir = args.dir[0]
    
    #Check the pvprefix for obvious mistakes
    if pvprefix == '':
        raise Exception("PVPREFIX not set - cannot run tests")
    if not pvprefix.endswith(':'):
        pvprefix = pvprefix + ':'
        
    #Load the tests
    iocname, tests = read_tests(filename)
    
    #Check for results directory
    if not os.path.isdir(results_dir):
        #Create it 
        os.makedirs(results_dir)

    #Set name for results file
    log_time = time.strftime('%Y-%m-%d %H-%M-%S', time.gmtime())
    logfile = ('%s %s Test Log.txt' % (log_time, iocname))
    logfile = os.path.join(results_dir, logfile)
    
    #Check the IOC name has a : at the end
    if not iocname.endswith(':'):
        iocname = iocname + ':'

    #First test for free - check  can put IOC in to simulation mode!
    pv_sim = PV(pvprefix + iocname + 'SIM')
    pv_sim.put("YES")
    time.sleep(DELAY)
    
    if pv_sim.get(as_string=True) == "YES":
        for t in tests:
            test_name = 'test_%s' % t[0]
            test = test_generator(pvprefix + iocname, t[1], t[2], t[3], t[4], t[5])
            setattr(TestSequence, test_name, test)
        
        #Open logfile, run tests, close file
        f = open(logfile, 'w')
        runner = unittest.TextTestRunner(f, verbosity=1)
        itersuite = unittest.TestLoader().loadTestsFromTestCase(TestSequence)
        runner.run(itersuite)
        f.close()
    else:
        #Give up here
        raise Exception("Error: could not put IOC into Simulation Mode")
    
        
    
    