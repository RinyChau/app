import os
import sys, traceback
import datetime
from werkzeug.utils import secure_filename

from dao.imagedb import ImageDB
from pyimagesearch.colordescriptor import ColorDescriptor
from pyimagesearch.searcher import Searcher
import urllib
from random import randint
import hashlib
import cv2

class ImgManagement:

    @staticmethod
    def saveFile(img_dir, image_file):
        file_name = secure_filename(image_file.filename)
        directory = ImgManagement.getTimeDir(img_dir)
        if not os.path.exists(directory):
            os.makedirs(directory)
        path = os.path.join(directory, file_name)
        while (os.path.isfile(path)):
            path = os.path.join(directory, file_name + str(randint(0, 1000)))
        image_file.save(path)
        print("save file" + path)
        return path

    @staticmethod
    def getMD5(path):
        hash_md5 = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    @staticmethod
    def deleteFile(path):
        os.remove(path)

    @staticmethod
    def saveUrl(url, img_dir):
        try:
            file = urllib.URLopener()
            directory = ImgManagement.getTimeDir(img_dir)
            path = os.path.join(directory, str(randint(0, 100000000)))
            while (os.path.isfile(path)):
                path = os.path.join(directory, str(randint(0, 100000000)))
            file.retrieve(url, path)
            md5 = ImgManagement.getMD5(path)
            if ImageDB.getItem({"md5": md5}) is not None:
                ImgManagement.deleteFile(path)
            else:
                image = cv2.imread(path)
                cd = ColorDescriptor((8, 12, 3))
                features = cd.describe(image)
                ImageDB.insert(md5, features, path)
        except:
            print("*** ImageManagement saveUrl takes error ***")
            print(sys.exc_info()[0])
            traceback.print_exc()
            print("*** ImageManagement saveUrl takes error ***")

    @staticmethod
    def getTimeDir(base_dir):
        year = str(datetime.datetime.now().year)
        month = str(datetime.datetime.now().month)
        day = str(datetime.datetime.now().day)
        hour = str(datetime.datetime.now().hour)
        directory = os.path.join(base_dir, year, month, day, hour)
        return directory