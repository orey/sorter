#---------------------------------
#-- Sorter python script
#-- Copyleft Olivier Rey 2018
#-- This utility sorts files and creates a timeline tree
#-- It is working per type
#---------------------------------

import hashlib
import sys
import time
import os
import PIL.Image
import PIL.ExifTags
import getopt

from datetime import datetime
from os import listdir
from os.path import isfile, join
from shutil import copyfile


FOLDER = '/home/olivier/.aMule/Incoming/'
EXT = '.jpg'
MINSIZE = 30000
MAXSIZE = 15000000

DATETAG1 = 'DateTimeOriginal'
DATETAG2 = 'DateTimeDigitized'

DATETIME1 = 'created'
DATETIME2 = 'lastmodif'

VERBOSE = False


DUP = 'duplicates'
SORTED = 'sorted'
ROOT = '/home/olivier/Temp'

#-- Stats
nb_folders = 0
nb_files   = 0
nb_dupes   = 0
    


def copyFile(src, key, dest):
    if not os.path.isfile(src):
        print("== Error: " + src + " is not a valid file") 
        return False
    if not os.path.isdir(dest):
        print("== Error: " + dest + " is not a valid folder")
    filename = os.path.basename(src)
    l = len(filename)
    temp = key + filename[:l-4] + EXT
    if os.path.isfile(temp):
        print("== Error: file " + temp + " already exists. Skipping...")
        return False
    tfn = join(dest, temp)
    copyfile(src, tfn)
    return True

def analyzePhoto(photo):
    """
    This method has 3 criterias that are applied in a sequence mode
    1. File name
    2. Tags
    3. File system information
    The oldest date time is considered the best
    """
    ld =[]
    #-- 1. Search for file name pattern 
    filename = os.path.basename(photo)
    if len(filename) > 14:
        chain = filename[:15]
        try:
            d = datetime.strptime(chain, '%Y%m%d_%H%M%S')
            ld.append(d)
        except ValueError:
            pass
    #-- 2. Analyze photo meta data
    #d = getExif(photo)
    #if (not d == None) and (not d == {}):
    #    try:
    #        ld.append(d[DATETAG1])
    #        ld.append(d[DATETAG2])
    #    except KeyError:
    #        pass
    #-- 3. File system
    d = getFileDate(photo)
    ld.append(d[DATETIME1])
    ld.append(d[DATETIME2])

    return min(ld)


def testCopyFile():
    p = '/home/olivier/photo.jpg'
    key = analyzePhoto(p)
    r = copyFile(p, key, '/home/olivier/Temp')
    if r:
        print("OK")
    else:
        print("NOT OK")

    
def createFolder(mypath):
    if not os.path.isdir(mypath):
        os.makedirs(mypath)


def createRoot(mypath, verbose=VERBOSE):
    if not os.path.isdir(mypath):
        print("== Error: " + mypath + " is not a valid folder. Exiting...")
        sys.exit(0)
    myroot = join(mypath, SORTED + "_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    createFolder(myroot)
    if verbose:
        print('Root path created: ' + myroot)
    sorted = join(myroot, SORTED)
    createFolder(sorted)
    if verbose:
        print('Sorted path created: ' + sorted)
    dup = join(myroot, DUP)
    createFolder(dup)
    if verbose:
        print('Duplicates path created: ' + dup)    
    return sorted, dup
    
def testCreateRoot():
    createRoot(ROOT)



def createName(dtime):
    return dtime.strftime("%Y%m%d_%H%M%S_%f")

def getExif(photo):
    """
    Extract photo datetime metadata or None
    """
    f = PIL.Image.open(photo)
    if f._getexif() == None:
        return None
    datetags = [DATETAG1,DATETAG2]
    exif = {}
    for k, v in f._getexif().items():
        try:
            a = PIL.ExifTags.TAGS[k]
        except KeyError:
            print("== Unknown tag for photo: " + photo)
            return None
        for tag in datetags:
            if a == tag:
                #-- v is '2016:09:04 11:06:58'
                exif[tag] = datetime.strptime(v, "%Y:%m:%d %H:%M:%S")
    return exif
    
def testGetExif():
    file1 = '/home/olivier/photo.jpg'
    file2 = '/home/olivier/photo2.jpg'
    d = getExif(file1)
    print(d)
    e = getExif(file2)
    print(e)
    a = getFileDate(file1)
    print(a)
    print(getFileDate(file2))
    print("Name of the file would be : " + createName(a['lastmodif']))
          
    

def getFileDate(file):
    return { DATETIME1 : datetime.fromtimestamp(os.path.getctime(file)), \
             DATETIME2 : datetime.fromtimestamp(os.path.getmtime(file)) }
    

def convertBytes(num):
    """
    this function will convert bytes to MB.... GB... etc
    """
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0


def fileOK(completename):
    """
    Filters the files not to generate hash for too small or too big
    files or for files with the wrong extension
    """
    if (not completename.endswith(EXT)) and (not completename.endswith(EXT.upper())) :
        return False
    fsize = os.stat(completename).st_size
    if fsize > MAXSIZE:
        if VERBOSE: print("== File: " + completename + " too big (" + \
                         convertBytes(fsize) + "). Excluding.")
        return False
    elif fsize < MINSIZE:
        if VERBOSE: print("== File: " + completename + " too small (" + \
                         convertBytes(fsize) + "). Excluding.")
        return False
    else:
        return True


def getFilesInFolder(mypath):
    """
    Returns two lists, the list of files and the list of subfolders
    All is managed with complete names
    The list of files is filtered
    """
    try:
        glob = listdir(mypath)
        files = []
        folders = []
        for f in glob:
            completef = join(mypath,f)
            if isfile(completef):
                if fileOK(completef):
                    files.append(completef)
            else:
                folders.append(completef)
        return files, folders
    except Exception:
        print("== Problem with folder: " + mypath)
        return None, None
        


def testGetFilesInFolder():
    files, folders = getFilesInFolder('/home/olivier/.aMule/Incoming')
    print("== Files:")
    print(files)
    print("== Folders:")
    print(folders)


def getHash(myfile, algo=0):
    """
    Generate hash for several algorithms
    """
    hasher = None
    if algo == 1:
        hasher = hashlib.sha1()
    else:
        hasher = hashlib.md5()
    with open(myfile, 'rb') as afile:
        buf = afile.read()
        hasher.update(buf)
    return hasher.hexdigest()



def createDict(dup, dict, folder, algo=0, verbose=VERBOSE):
    """
    Creates a dict with a hash and the file in order to spot the duplicate files
    even if they don't have the same names
    Warning: This function is recursive.
    """
    global nb_folders
    global nb_files
    global nb_dupes
    nb_folders += 1
    files, folders = getFilesInFolder(folder)
    if files == None:
        return dict;
    if verbose:
        print("\n== Folder: " + folder)
        print("== " + str(len(files)) + " files found with matching filter")
    dupes = 0
    keys = 0
    for completename in files:
        h = getHash(completename, algo)
        keys +=1
        sys.stdout.write(str(keys) + "|")
        sys.stdout.flush()
        try:
            temp = dict[h]
            #print('\n== Found duplicate of ' + "'" + completename + "'")
            #print("== '" + temp + "'")
            sys.stdout.write("DUP|")
            sys.stdout.flush()
            dupes += 1
            # Create folder for dup
            pathkey = join(dup, h)
            if not os.path.isdir(pathkey):
                createFolder(pathkey)
                copyFile(completename, "", pathkey)
            copyFile(temp, datetime.now().strftime("%Y%m%d_%H%M%S_%f_"), pathkey)
            nb_dupes +=1
        except KeyError:
            nb_files += 1
            dict[h] = completename
    if len(folders) == 0 or folders == None:
        return dict
    for d in folders:
        createDict(dup, dict, d, algo)
    return dict

def copyPhotoToDateFolder(photo, sorted):
    mdate = analyzePhoto(photo)
    year = join(sorted, str(mdate.year))
    createFolder(year) #manages the case when it already exists
    month = join(year, str(mdate.month).zfill(2))
    createFolder(month)
    #day = join(month, str(mdate.day).zfill(2))
    #createFolder(day)
    copyFile(photo, "",month)


def parseDictForCopies(dict, sorted):
    values = dict.values()
    print("Found " + str(len(values)) + " images")
    for v in values:
        copyPhotoToDateFolder(v, sorted)






def compareHash():
    global VERBOSE
    VERBOSE = False
    start1 = time.time()
    dict1 = {}
    createDict(dict1, '/home/olivier/.aMule/Incoming')
    end1 = time.time()

    start2 = time.time()
    dict2 = {}
    createDict(dict2, '/home/olivier/.aMule/Incoming', 1)
    end2 = time.time()

    print("\n== Generated " + str(len(dict1)) + " MD5 keys")
    print("== Execution time with md5: " + str(end1 - start1))
    print("\n== Generated " + str(len(dict2)) + " SHA1 keys")
    print("== Execution time with sha1: " + str(end2 - start2))
    

def printStats():
    print("=====================================")
    print("== Number of folders explored: " + str(nb_folders))
    print("== Number of files exploredin dict: " + str(nb_files))
    print("== Number of dupes: " + str(nb_dupes))
    print("=====================================")
    
def test_cases():
    mydir = '/home/olivier/olivier'
    verbose = True
    time1 = time.time()
    sorted, dup = createRoot(ROOT,verbose)
    dict = {}
    createDict(dup, dict, mydir, 1, True)
    time2 = time.time()
    print("=====================================")
    print("== Spent: " + str(time2-time1))
    print("=====================================")
    printStats()
    parseDictForCopies(dict, sorted)
    printStats()


def usage():
    '''
    Usage function
    '''
    print('Sorter program: finds all duplicates in a tree and sorts them' + \
          ' in a timeline')
    print('$ python3 sorter.py -e jpg -i /home/toto/rootfolder -o /home/toto/temp')
    print('Other options:')
    print('"-v" verbose mode')
    print('"-h" usage')
    

def main():
    try:
        # Option 't' is a hidden option
        opts, args = getopt.getopt(sys.argv[1:], "e:i:o:hvt",
                                   ["extension=", "inputdir=", \
                                   "outputdir=","help", \
                                   "verbose", "test"])
    except getopt.GetoptError:
        # print help information and exit:
        usage()
        sys.exit(2)
    # init option keys
    extension = ""
    inputdir = ""
    outputdir = ""
    verbose = False
    test    = False
    # parsing options
    for k, v in opts:
        if k in ("-e", "--extension"):
            extension = v
        if k in ("-i", "--inputdir"):
            inputdir = v
        if k in ("-o", "--outputdir"):
            outputdir = v
        if k in ("-h", "--help"):
            usage()
            sys.exit(0)
        if k in ("-v", "--verbose"):
            verbose = True
        if k in ('-t', '--test'):
            test = True
    # Test scenario
    if test:
        test_cases()
        sys.exit(0)
    if extension == '' or inputdir == '' or outputdir == '':
        print('Warning: the 3 parameters are required: "-e", "-i" and "-o"')
        usage()
        sys.exit(0)
    if not os.path.exists(inputdir):
        print('Warning: input dir not existing: ' + inputdir)
        usage()
        sys.exit(0)
    if not os.path.exists(outputdir):
        print('Warning: output dir not existing: ' + outputdir)
        try:
            os.makedirs(outputdir)
        except OSError as e:
            print('Error: could not create: ' + outputdir + ". Exiting.")
            print(e)
            sys.exit(1)
    print('No feature implemented')
    print('extension = ' + extension)
    print('inputdir = ' + inputdir)
    print('outputdir = ' + outputdir)






    
    
if __name__ == "__main__":
    main()
    #testGetFilesInFolder()
    #compareHash()
    #testGetExif()
    #testCreateRoot()
    #testSorted()
    #testCopyFile()






