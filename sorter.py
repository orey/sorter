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
from enum import Enum
from PIL import Image
from PIL.ExifTags import TAGS

class Algo(Enum):
    MD5  = 0
    SHA1 = 1


class Action(Enum):
    BROWSE = 0
    COPY   = 1
    MOVE   = 2

#-- Stats
class Stats():
    nb_folders = 0
    nb_files   = 0
    nb_dupes   = 0

STATS = Stats()

JPG = ['jpg', 'JPG', 'jpeg', 'JPEG']
JPG_DateTime  = 'DateTime'
JPG_DateTimeOriginal  = 'DateTimeOriginal'
JPG_DateTimeDigitized = 'DateTimeDigitized'
JPG_DatePattern = '%Y:%m:%d %H:%M:%S'

FileNamePatterns = {'SamsungFileName' : '%Y%m%d_%H%M%S'}

FileCreationDate = 'FileCreationDate'
FileLastModif = 'FileLastModification'

ImportanceOrder = ['SamsungFileName','DateTimeOriginal','DateTimeDigitized', \
                   'FileCreationDate','FileLastModification']




EXT = '.jpg'
MINSIZE = 10000
MAXSIZE = 500000000


VERBOSE = False


DUP = 'duplicates'
SORTED = 'sorted'
ROOT = '/home/olivier/Temp'



# OK
def copy_file_with_key(f, key, dest):
    if not os.path.isfile(f):
        print("== Error: " + f + " is not a valid file") 
        return False
    if not os.path.isdir(dest):
        print("== Error: " + dest + " is not a valid folder")
        return False
    tfn = join(dest, key + os.path.basename(f))
    if os.path.isfile(tfn):
        print("== Warning: file " + tfn + " already exists. Skipping...")
        return False
    copyfile(f, tfn)
    return True


# OK
def test_copy_file_with_key():
    copy_file_with_key('/home/olivier/photo.jpg', 'abcde_','/home/olivier/Temp')
    copy_file_with_key('/home/olivier/toto.pdf', 'abcde_','/home/olivier/Temp')


# OK
def check_jpg_file(f):
    if not os.path.isfile(f):
        print("== Error: " + f + " is not a valid file") 
        return False
    filename = os.path.basename(f)
    extension = filename.split('.')[-1]
    if extension not in JPG:
        return False
    return True


# OK
def get_jpg_exif(fn, verbose=False):
    ret = {}
    # Check file type
    if not check_jpg_file(fn):
        print('Warning: File is not a JPEG file: ' + fn + '. Skipping...')
        return None
    i = Image.open(fn)
    info = i._getexif()
    if info == None:
        return None
    for tag, value in info.items():
        decoded = TAGS.get(tag, tag)
        if 'DATE' in str(decoded).upper():
            d = None
            try:
                d = datetime.strptime(value, JPG_DatePattern)
            except ValueError:
                if verbose:
                    print('Unrecognized date pattern: ' + str(value))
                else:
                    pass
            ret[decoded] = d
    return ret


# OK
def test_photo():
    mydir = '/home/olivier/Pictures/Test_sorter/'
    def test_single(name):
        ret = get_jpg_exif(mydir + name)
        print(name)
        print(ret)
    test_single('20161213_200803.JPG')
    test_single('test1.jpg')
    test_single('test2.jpg')
    test_single('test3.jpeg')
    test_single('test4.jpg')
    test_single('test5.jpg')
    test_single('2016-12-07-13-49-54.png')
    

# OK
def analyze_photo(photo, verbose=False):
    """
    This method has 3 criterias that are applied in a sequence mode
    1. File name
    2. Tags
    3. File system information
    The oldest date time is considered the best
    """
    # Will store the dates
    ld ={}
    #-- 1. Search for file name pattern 
    filename = os.path.basename(photo)
    # Remove extension
    chain = filename.replace('.' + filename.split('.')[-1], '')
    for name, pattern in FileNamePatterns.items():
        try:
            # TODO Should introduce a regular expression based treatment here
            d = datetime.strptime(chain, pattern)
            ld[name] = d
        except ValueError:
            pass
    #-- 2. Analyze photo meta data
    # TODO : manage specific PNG tags
    tags = get_jpg_exif(photo, verbose)
    if tags != None:
        for k, v in tags.items():
            ld[k] = v
    #-- 3. File system
    ld[FileCreationDate] = datetime.fromtimestamp(os.path.getctime(photo))
    ld[FileLastModif] = datetime.fromtimestamp(os.path.getmtime(photo))
    if verbose:
        print(ld)
    for k in ImportanceOrder:
        if k in ld.keys():
            if verbose:
                print('Chosen date: ' + k)
            return ld[k]
    raise Exception('No dates found. This case should not happen.')
            

# OK
def test_analyze_photo():
    analyze_photo('/home/olivier/Pictures/Test_sorter/20161213_200803.JPG', True)


# OK
def create_folder(mypath):
    if not os.path.isdir(mypath):
        os.makedirs(mypath)

# OK
def create_root(mypath, verbose=False):
    if not os.path.isdir(mypath):
        print("== Error: " + mypath + " is not a valid folder. Exiting...")
        sys.exit(0)
    myroot = join(mypath, SORTED + "_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    create_folder(myroot)
    if verbose:
        print('Root path created: ' + myroot)
    sorted = join(myroot, SORTED)
    create_folder(sorted)
    if verbose:
        print('Sorted path created: ' + sorted)
    dup = join(myroot, DUP)
    create_folder(dup)
    if verbose:
        print('Duplicates path created: ' + dup)    
    return sorted, dup


# OK
def test_create_root():
    create_root('/home/olivier/Temp')


# OK
def convert_bytes(num):
    """
    this function will convert bytes to MB.... GB... etc
    """
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0


# OK
def filter_by_type_and_size(completename, extensionlist, minsize=MINSIZE, maxsize=MAXSIZE, verbose=False):
    """
    Filters the files not to generate hash for too small or too big
    files or for files with the wrong extension
    """
    # Get extension
    if completename.split('.')[-1] not in extensionlist:
        return False
    fsize = os.stat(completename).st_size
    print(completename)
    print(fsize)
    if int(fsize) > maxsize:
        if verbose: print("== File: " + completename + " too big (" + \
                         convert_bytes(fsize) + "). Excluding.")
        return False
    elif int(fsize) < minsize:
        if verbose: print("== File: " + completename + " too small (" + \
                         convert_bytes(fsize) + "). Excluding.")
        return False
    else:
        return True


# OK
def get_files_in_folder(mypath, extensionlist, minsize=MINSIZE, maxsize=MAXSIZE, verbose=False):
    """
    Returns two lists, the list of files and the list of subfolders
    All is managed with complete names
    The list of files is filtered with extension
    """
    try:
        glob = listdir(mypath)
        files = []
        folders = []
        for f in glob:
            completef = join(mypath,f)
            if isfile(completef):
                if filter_by_type_and_size(completef, extensionlist, minsize, maxsize, verbose):
                    files.append(completef)
            else:
                folders.append(completef)
        return files, folders
    except Exception:
        print("== Problem with folder: " + mypath)
        return None, None


# OK
def test_get_files_in_folder():
    files, folders = get_files_in_folder('/home/olivier/Documents/Bibliothèque', ['pdf', 'PDF'], 10000000, 20000000, True)
    print("== Files:")
    print(files)
    print("== Folders:")
    print(folders)


# OK
def get_hash(myfile, algo=Algo.MD5, verbose=False):
    """
    Generate hash for several algorithms
    """
    hasher = None
    if algo == Algo.MD5:
        hasher = hashlib.md5()
    elif algo == Algo.SHA1:
        hasher = hashlib.sha1()
    else:
        raise ValueError('Unknown algorithm:' + str(algo))
    with open(myfile, 'rb') as afile:
        buf = afile.read()
        hasher.update(buf)
    return hasher.hexdigest()


# OK
def create_dict(mydict, folder, ext = '.jpg', algo=Algo.MD5, action=Action.BROWSE, dup=None, verbose=False):
    """
    Creates a dict with a hash and the file in order to spot the duplicate files
    even if they don't have the same names.
    This function does a certain action with the files.
    Warning: This function is recursive.
    """
    STATS.nb_folders += 1
    files, folders = getFilesInFolder(folder, ext, verbose)
    if files == None:
        return mydict;
    if verbose:
        print("\n== Folder: " + folder + ' - ' + str(len(files)) + " files found")
    dupes = 0
    # For display in verbose mode only
    keys = 0
    for completename in files:
        h = get_hash(completename, algo)
        keys +=1
        if verbose:
            sys.stdout.write(str(keys) + "|")
            sys.stdout.flush()
        try:
            temp = mydict[h]
            if verbose:
                sys.stdout.write("DUP|")
                sys.stdout.flush()
            dupes += 1
            if action == Action.COPY:
                # Create folder for dup
                pathkey = join(dup, h)
                if not os.path.isdir(pathkey):
                    create_folder(pathkey)
                    copy_file_with_key(completename, "", pathkey)
                else:
                    copy_file_with_key(temp, datetime.now().strftime("%Y%m%d_%H%M%S_%f_"), pathkey)
            elif action == Action.MOVE:
                raise ValueError('Move action not implemented')
            elif action == Action.BROWSE:
                pass
            else:
                raise ValueError('Unknown action: ' + str(action))
            STATS.nb_dupes +=1
        except KeyError:
            # The file is new
            STATS.nb_files += 1
            mydict[h] = completename
    # Analyze folders
    if len(folders) == 0 or folders == None:
        return mydict
    for d in folders:
        createDict(mydict, d, ext, algo, action, dup, verbose)
    return mydict


def copyPhotoToDateFolder(photo, sorted, ext):
    mdate = analyzePhoto(photo)
    year = join(sorted, str(mdate.year))
    create_folder(year) #manages the case when it already exists
    month = join(year, str(mdate.month).zfill(2))
    create_folder(month)
    #day = join(month, str(mdate.day).zfill(2))
    #createFolder(day)
    copy_file_with_key(photo, "",month)


def parseDictForCopies(dict, sorted, ext):
    values = dict.values()
    print("Found " + str(len(values)) + " images")
    for v in values:
        copyPhotoToDateFolder(v, sorted, ext)





# OK
def test_hash_perf(verbose=True):
    testdir = '/home/olivier/.aMule/Incoming'
    start1 = time.time()
    dict1 = {}
    create_dict(dict1, testdir, '.pdf', Algo.MD5, Action.BROWSE, None, verbose)
    end1 = time.time()
    print("\n== Generated " + str(len(dict1)) + " MD5 keys")
    print("== Execution time with md5: " + str(end1 - start1))

    start2 = time.time()
    dict2 = {}
    create_dict(dict2, testdir, '.pdf', Algo.SHA1, Action.BROWSE, None, verbose)
    end2 = time.time()
    print("\n== Generated " + str(len(dict2)) + " SHA1 keys")
    print("== Execution time with sha1: " + str(end2 - start2))
    return 'Test complete'
    

def printStats():
    print("=====================================")
    print("== Number of folders explored: " + str(STATS.nb_folders))
    print("== Number of files exploredin dict: " + str(STATS.nb_files))
    print("== Number of dupes: " + str(STATS.nb_dupes))
    print("=====================================")
    
def test_cases():
    mydir = '/home/olivier/olivier'
    verbose = True
    time1 = time.time()
    sorted, dup = create_root(ROOT,verbose)
    dict = {}
    createDict(dup, dict, mydir, '.jpg', 1, True)
    time2 = time.time()
    print("=====================================")
    print("== Spent: " + str(time2-time1))
    print("=====================================")
    parseDictForCopies(dict, sorted, '.jpg')
    printStats()

    
def treatment(mytype, inputdir, outputdir, verbose):
    time1 = time.time()
    # create the destination tree with a unique folder name
    msorted, dup = create_root(outputdir, verbose)
    mydict = {}
    createDict(dup, mydict, inputdir, mytype, 1, verbose)
    time2 = time.time()
    if verbose:
        print("=====================================")
        print("== Spent: " + str(time2-time1))
        print("=====================================")
    parseDictForCopies(mydict, msorted, mytype)
    printStats()


def tests():
    test_hash_perf(False)
    test_create_root()
    

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
            extension = '.' + v
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
    if verbose:
        print('extension = ' + extension)
        print('inputdir = ' + inputdir)
        print('outputdir = ' + outputdir)
    treatment(extension, inputdir, outputdir, verbose)
    
    
if __name__ == "__main__":
    main()
    #testGetFilesInFolder()
    #compareHash()
    #testGetExif()
    #testcreate_root()
    #testSorted()
    #testcopy_file()






