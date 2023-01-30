#!/usr/bin/env python

import os
import subprocess
from numpy.random import RandomState

### GENERAL PARAMETERS ###
numcomp = 25
maxcid = 10000

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# define a function which goes back to the original working directory if it is called
def odir(pwdorg):
    try:
        os.chdir(str(pwdorg))
        # print("Current working directory: {0}".format(os.getcwd()))
    except FileNotFoundError:
        print("Directory does not exist".format(i))
    except NotADirectoryError:
        print("{0} is not a directory" % pwdorg)

# set the seed
print("Generating random numbers between 1 and %d ..." % maxcid)
seed = RandomState(2009)
values = seed.randint(1, maxcid, size=3*numcomp)
print("Done.")

pwd = os.getcwd()

# run PubGrep for each value and set up a list with successful downloads
comp = []
for i in values:
    print("\nDownloading CID %6d ..." % i)
    try:
        pgout = subprocess.run(
            ["PubGrep", "--input", "cid", str(i)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30)
    except subprocess.TimeoutExpired as exc:
        print(f"Process timed out.\n{exc}")
        continue
    except subprocess.CalledProcessError as exc:
        print("Status : FAIL", exc.returncode, exc.output)
        continue

    # print the return code
    if pgout.returncode != 0:
        print("Return code:", pgout.returncode)

    if pgout.stderr.decode("utf-8") == "":
        print(' '*3 + "Downloaded   %6d successfully." % i)
    else:
        if "abnormal termination" in pgout.stderr.decode("utf-8"):
            print(' '*3 + f"{bcolors.WARNING}xTB error in conversion process - skipping CID %6d {bcolors.ENDC}" % i)
            continue
        elif not "normal termination" in pgout.stderr.decode("utf-8"):
            print(' '*3 + f"{bcolors.WARNING}Unknown PubGrep/xTB conversion error - skipping CID %6d{bcolors.ENDC}" % i)
            errmess="PubGrep_error" + str(i) + ".err"
            with open(errmess, "w") as f:
                f.write(pgout.stderr.decode("utf-8"))
            continue
        else:
            print(' '*3 + "Downloaded   %6d successfully after xTB conversion." % i)

    try:
        os.chdir(str(pwd) + "/pubchem_compounds/" + str(i))
        # print("Current working directory: {0}".format(os.getcwd()))
    except FileNotFoundError:
        print("Directory: /pubchem_compounds/{0} does not exist".format(i))
    except NotADirectoryError:
        print("/pubchem_compounds/{0} is not a directory".format(i))
    except PermissionError:
        print("You do not have permissions to change to /pubchem_compounds/{0}".format(i))


    try:
        pgout = subprocess.run(["mctc-convert", "{0}.sdf".format(i), "struc.xyz"],
                           check=True,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,
                           timeout=120)
    except subprocess.TimeoutExpired as exc:
        print(' '*3 + f"Process timed out.\n{exc}")
        odir(pwd)
        continue
    except subprocess.CalledProcessError as exc:
        print(' '*3 + "Status : FAIL", exc.returncode, exc.output)
        # write the error output to a file
        with open("mctc-convert_error.err", "w") as f:
            f.write(pgout.stderr.decode("utf-8"))
        print(f"{bcolors.WARNING}xTB optimization failed - skipping CID %6d{bcolors.ENDC}" % i)
        odir(pwd)
        continue

    # check if first line of struc.xyz is not larger than 50
    with open("struc.xyz", "r") as f:
        first_line = f.readline()
        if int(first_line.split()[0]) > 50:
            print(f"{bcolors.WARNING}Number of atoms in struc.xyz is larger than 50 - skipping CID %6d{bcolors.ENDC}" % i)
            odir(pwd)
            continue

    try:
        pgout = subprocess.run(["xtb", "struc.xyz", "--opt"],
                           check=True,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,
                           timeout=120)
    except subprocess.TimeoutExpired as exc:
        print(' '*3 + f"Process timed out.\n{exc}")
        odir(pwd)
        continue
    except subprocess.CalledProcessError as exc:
        print(' '*3 + f"{bcolors.FAIL}Status : FAIL{bcolors.ENDC}", exc.returncode)
        with open("xtb_error.err", "w") as f:
            f.write(exc.output.decode("utf-8"))
        print(f"{bcolors.WARNING}xTB optimization failed - skipping CID %6d{bcolors.ENDC}" % i)
        odir(pwd)
        continue
    # print return code
    if pgout.returncode != 0:
        print("Return code:", pgout.returncode)

    odir(pwd)

    print(f"{bcolors.OKGREEN}Structure of    %6d successfully generated and optimized.{bcolors.ENDC}" % i)
    comp.append(i)
    print("[" + str(len(comp)) + "/" + str(numcomp) + "]")
    if len(comp) >= numcomp:
        break

# print number of successful downloads
print("\n\nNumber of successful downloads: ", len(comp))
print("Compounds: ", comp)
