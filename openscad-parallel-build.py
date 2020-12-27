#!/usr/bin/env python3

# Include dependencies
import os
import sys
import multiprocessing
import queue
import threading
import subprocess
import platform
import shutil

# Global vars
possibleWorkers = multiprocessing.cpu_count()
queue = queue.Queue()
queueLock = threading.Lock()
workers = []
OPENSCAD_PATH = None
SOURCE_PATH = None
DESTINATION_PATH = None

# Worker class
class workerThread(threading.Thread):
    def __init__(self, id, queue, lock):
        threading.Thread.__init__(self)
        self.__id = id
        self.__lock = lock
        self.__queue = queue

    def run(self):
        while True:
            self.__lock.acquire()
            if not self.__queue.empty():
                workCommand = self.__queue.get()
                self.__lock.release()
                commandTuple = workCommand.getCommand()
                processCommand = [OPENSCAD_PATH, "-o", DESTINATION_PATH + "/out/" + commandTuple[0]]
                for variable in commandTuple[2]:
                    processCommand.append("-D")
                    processCommand.append(variable)
                processCommand.append(SOURCE_PATH + "/" + commandTuple[1])
                scad = subprocess.Popen(processCommand, stdout=subprocess.PIPE)
                scad.communicate()
                scad.wait()
                workCommand.finish()
            else:
                self.__lock.release()
                break

# Job class
class compileJob:
    def __init__(self, file, accuracy, renderId, disableTest):
        self.__file = file
        self.__accuracy = accuracy
        self.__renderId = renderId
        self.__disableTest = disableTest

    def getCommand(self):
        variable = []
        outExtend = ""
        if not self.__renderId == None:
            outExtend = "_" + str(self.__renderId)
        if not self.__renderId == None:
            variable.append("EXPORT_MODE=" + str(self.__renderId))
        if self.__disableTest:
            variable.append("TEST_MODE=0")
        if not self.__accuracy == None:
            with open(SOURCE_PATH + "/" + self.__file, "r") as f:
                lines = f.readlines()
            with open(SOURCE_PATH + "/" + self.__file[:-5] + "_temp.scad", "w") as f:
                for l in lines:
                    if "$fn" in l:
                        f.write("$fn=" + str(self.__accuracy) + ";\n")
                    else:
                        f.write(l)
            return (self.__file[:-5] + outExtend + ".stl", self.__file[:-5] + "_temp.scad", variable)
        else:
            return (self.__file[:-5] + outExtend + ".stl", self.__file, variable)

    def finish(self):
        if not self.__accuracy == None:
            os.remove(SOURCE_PATH + "/" + self.__file[:-5] + "_temp.scad")

# FUNCTIONS
# Path checking function
def checkFolderPaths(PATH):
    if not os.path.exists(PATH):
        return 1
    elif not os.path.isdir(PATH):
        return 2
    elif not os.access(PATH, os.W_OK):
        return 3
    return 0

# Clear and delete folder
def deleteFolder(folder):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))
    os.rmdir(folder)

# Extract compile jobs from a .scad file
def extractJobs(file):
    jobs = []
    hasDifferentAccuracy = None
    jobId = None
    hasTestMode = False
    isPropertiesLine = False
    with open(SOURCE_PATH + "/" + file, "r") as f:
        for line in f.readlines():
            if isPropertiesLine:
                if line.startswith("AVAILABLE_MODES"):
                    parts = line.split("=")
                    jobId = int(parts[1].strip().replace(";", ""))
                elif line.startswith("RENDER_WITH"):
                    parts = line.split("=")
                    hasDifferentAccuracy = int(parts[1].strip().replace(";", ""))
                elif line.startswith("TEST_MODE"):
                    hasTestMode = True
            elif line.strip() == "//END-PARALLEL-PROPS":
                isPropertiesLine = False
                break
            elif line.strip() == "//PARALLEL-PROPS":
                isPropertiesLine = True
    if jobId == None:
        jobs.append(compileJob(file, hasDifferentAccuracy, None, hasTestMode))
    else:
        for i in range(0, jobId):
            jobs.append(compileJob(file, hasDifferentAccuracy, i, hasTestMode))
    return jobs

# MAIN PROGRAM
# Evaluate CLI parameters
if not len(sys.argv) == 3:
    print("Wrong number of parameters.")
    print("Usage: openscad-parallel-build.py /path/to/source-folder /path/to/destination-folder")
    sys.exit()
else:
    SOURCE_PATH = sys.argv[1]
    DESTINATION_PATH = sys.argv[2]
    sourceCheck = checkFolderPaths(SOURCE_PATH)
    destinationCheck = checkFolderPaths(DESTINATION_PATH)
    if not sourceCheck == 0 and not destinationCheck == 0:
        if sourceCheck == 1:
            print("Source path not found. Aborting.")
        elif sourceCheck == 2:
            print("Source path is not a directory. Aborting.")
        elif destinationCheck == 1:
            print("Destination path is not found. Aborting.")
        elif destinationCheck == 1:
            print("Destination path is not a directory. Aborting.")
        elif destinationCheck == 1:
            print("Unable to write to destination path. Aborting.")
        print("The script failed due to parameter errors. Check your input and try again.")
        sys.exit()
    else:
        if DESTINATION_PATH.endswith("/"):
            DESTINATION_PATH = DESTINATION_PATH[:-1]
        if SOURCE_PATH.endswith("/"):
            SOURCE_PATH = SOURCE_PATH[:-1]

# Check if we find OpenSCAD
OS = platform.system()
if OS == "Darwin":
    OPENSCAD_PATH = "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
elif OS == "Linux":
    OPENSCAD_PATH = "/usr/bin/openscad"
elif OS == "Windows":
    OPENSCAD_PATH = ""
while not os.path.exists(OPENSCAD_PATH):
    print("Unable to find OpenSCAD. You can manually provide a path.")
    OPENSCAD_PATH = input("OpenSCAD executable: ")
    if os.path.exists(OPENSCAD_PATH):
        break

# Create the destination directory
if os.path.exists(DESTINATION_PATH + "/out"):
    print("There is already a folder called 'out' in your destination path. Should I remove it? Type 'DELETE'")
    confirmation = input("Remove 'out' in your destination path? ")
    if confirmation == "DELETE":
        deleteFolder(DESTINATION_PATH + "/out")
    else:
        print("Aborting.")
        sys.exit()

# Create output folder
os.mkdir(DESTINATION_PATH + "/out")

# Check files for jobs, add them to queue
queueLock.acquire()
for file in os.listdir(SOURCE_PATH):
    if file.endswith(".scad"):
        for job in extractJobs(file):
            queue.put(job)
queueLock.release()

# Create worker threads based on cpu count
for x in range(0, possibleWorkers):
    thread = workerThread(x, queue, queueLock)
    thread.start()
    workers.append(thread)

# Start worker threads and wait for them to end
for thread in workers:
    thread.join()
