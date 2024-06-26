#!/usr/bin/env python

import os
import sys
import subprocess
import numpy as np

# get number of compounds from command line
numarg = len(sys.argv)
if numarg < 2:
    print("No number of compounds specified. Using default value of 2.\n")
    numcomp = 2
elif numarg > 2:
    print("Too many arguments. Error stop.")
    exit(1)
else:
    numcomp = int(sys.argv[1])

### GENERAL PARAMETERS ###
MAXCID = 10000000
MAXNUMAT = 50


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
        print(f"Directory {pwdorg} does not exist")
    except NotADirectoryError:
        print(f"{pwdorg} is not a directory")


# set the seed
print(f"Generating random numbers between 1 and {MAXCID} ...")
seed = np.random.default_rng()
values = seed.integers(1, MAXCID, size=3 * numcomp)
print("Done.")

pwd = os.getcwd()

# run PubGrep for each value and set up a list with successful downloads
comp = []
molname = []
for i in values:
    print(f"\nDownloading CID {i} ...")
    try:
        pgout = subprocess.run(
            ["PubGrep_dev", "--input", "cid",
             str(i), "--fast"],
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
        print(' ' * 3 + "Downloaded   %7d successfully." % i)
    else:
        if "abnormal termination" in pgout.stderr.decode("utf-8"):
            print(
                ' ' * 3 +
                f"{bcolors.WARNING}xTB error in conversion process - skipping CID %7d {bcolors.ENDC}"
                % i)
            continue
        elif "normal termination" not in pgout.stderr.decode("utf-8"):
            print(
                ' ' * 3 +
                f"{bcolors.WARNING}Unknown PubGrep/xTB conversion error - skipping CID %7d{bcolors.ENDC}"
                % i)
            errmess = "PubGrep_error" + str(i) + ".err"
            with open(errmess, "w") as f:
                f.write(pgout.stderr.decode("utf-8"))
            continue
        else:
            print(' ' * 3 +
                  "Downloaded   %7d successfully after xTB conversion." % i)

    try:
        os.chdir(str(pwd) + "/pubchem_compounds/" + str(i))
        # print("Current working directory: {0}".format(os.getcwd()))
    except FileNotFoundError:
        print("Directory: /pubchem_compounds/{0} does not exist".format(i))
    except NotADirectoryError:
        print("/pubchem_compounds/{0} is not a directory".format(i))
    except PermissionError:
        print(
            "You do not have permissions to change to /pubchem_compounds/{0}".
            format(i))

    # print the first entry of the fourth line compund of interest in sdf format
    with open("{0}.sdf".format(i), "r") as f:
        lines = f.readlines()
        nat = int(lines[3].split()[0])
        print(' ' * 3 + "# of atoms: {0:8d}".format(nat))
        if int(nat) > MAXNUMAT:
            print(
                f"{bcolors.WARNING}Number of atoms in {i}.sdf is larger than {MAXNUMAT} - skipping CID {i:7d}{bcolors.ENDC}"
            )
            odir(pwd)
            continue

    try:
        pgout = subprocess.run(["xtb", "{0}.sdf".format(i), "--opt"],
                               check=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               timeout=120)
        with open("xtb.out", "w") as f:
            f.write(pgout.stdout.decode("utf-8"))
    except subprocess.TimeoutExpired as exc:
        print(' ' * 3 + f"Process timed out.\n{exc}")
        odir(pwd)
        continue
    except subprocess.CalledProcessError as exc:
        print(' ' * 3 + f"{bcolors.FAIL}Status : FAIL{bcolors.ENDC}",
              exc.returncode)
        with open("xtb_error.out", "w") as f:
            f.write(exc.output.decode("utf-8"))
        with open("xtb_error.err", "w") as f:
            f.write(pgout.stderr.decode("utf-8"))
        print(
            f"{bcolors.WARNING}xTB optimization failed - skipping CID %7d{bcolors.ENDC}"
            % i)
        odir(pwd)
        continue

    # load fourth entry of a line with ":: total charge" of xtb.out into a variable
    chrg=0
    with open("xtb.out", "r") as f:
        lines = f.readlines()
        for line in lines:
            if ":: total charge" in line:
                chrg = round(float(line.split()[3]))
    print(' ' * 3 + "Total charge: {0:6d}".format(chrg))
    # write chrg to a file called .CHRG
    with open(".CHRG", "w") as f:
        f.write(str(chrg)+"\n")

    try:
        pgout = subprocess.run(["mctc-convert", "xtbopt.sdf", "struc.xyz"],
                               check=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               timeout=120)
    except subprocess.TimeoutExpired as exc:
        print(' ' * 3 + f"Process timed out.\n{exc}")
        odir(pwd)
        continue
    except subprocess.CalledProcessError as exc:
        print(' ' * 3 + "Status : FAIL", exc.returncode, exc.output)
        # write the error output to a file
        with open("mctc-convert_error.err", "w") as f:
            f.write(pgout.stderr.decode("utf-8"))
        print(
            f"{bcolors.WARNING}mctc-convert failed - skipping CID %7d{bcolors.ENDC}"
            % i)
        odir(pwd)
        continue

    odir(pwd)

    # grep the name of the molecule from found.results (first entry in first line)
    with open("found.results", "r") as f:
        first_line = f.readline()
        molname.append(first_line.split()[0])
        print(' ' * 3 + "Compound name: %s" % molname[-1])

    print(
        f"{bcolors.OKGREEN}Structure of    %7d successfully generated and optimized.{bcolors.ENDC}"
        % i)
    comp.append(i)
    print("[" + str(len(comp)) + "/" + str(numcomp) + "]")
    if len(comp) >= numcomp:
        break

# print number of successful downloads
print("\nNumber of successful downloads: ", len(comp))
print("Compounds: ", comp)

# write the list of successful downloads to a file
with open("compounds.txt", "w") as f:
    for i in comp:
        f.write(str(i) + " " + molname[comp.index(i)] + "\n")
os.remove("found.results")
