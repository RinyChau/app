from pyimagesearch.colordescriptor import ColorDescriptor
import argparse
import glob
import cv2
import datetime
import hashlib
import numpy as np
from pymongo import MongoClient
from PIL import Image
from pyimagesearch.colordescriptor import Feature
from sklearn_theano.feature_extraction import GoogLeNetClassifier
import imagehash
from helper import PicklePoints
import urllib, cStringIO
import time
import os

def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


ap = argparse.ArgumentParser()
ap.add_argument("-d", "--dataset", required=True,
                help="Path to the directory that contains the images to be indexed")
ap.add_argument("-u", "--url", required=False,
                help="Path to the url directory that contains the images to be indexed")
args = vars(ap.parse_args())

# initialize mongodb client
client = MongoClient()

# Content-based image retrieval database
db = client.CIBR
collection = db.ImageFeature
# initialize the color descriptor
hsv_cd = ColorDescriptor((8, 12, 3), feature=Feature.HSV)
luv_cd = ColorDescriptor(feature=Feature.LUV)
top_n_classes = 5
clf = GoogLeNetClassifier(top_n=top_n_classes)
start_time = time.time()
count = 0

all_imgs = []
for path, subdirs, files in os.walk(args["dataset"]):
    for name in files:
        all_imgs.append(os.path.join(path, name))

# use glob to grab the image paths and loop over them
for imagePath in all_imgs:
    # extract the image ID (i.e. the unique filename) from the image
    try:
        im = Image.open(imagePath)
    except:
        print("cannot get image" + imagePath)
        continue

    file_md5 = md5(imagePath)
    same_imgs = list(collection.find({"": file_md5}))
    if len(same_imgs) > 0:
        print("same image" + imagePath)
        continue
    # path and load the image itself
    imgObj = {}
    imgObj["ImageName"] = imagePath[imagePath.rfind("/") + 1:]
    image_url = None

    if 'url' in args and args['url'] is not None:
        image_url = args['url'].strip('/') + '/' + imgObj["ImageName"]
        file = cStringIO.StringIO(urllib.urlopen(image_url).read())
        image_src = Image.open(file)
        image = np.array(image_src)

    if image_url is None:
        image_src = Image.open(imagePath)
        image = np.array(image_src)

    imgObj[Feature.HSV] = [x for x in hsv_cd.describe(image)]
    imgObj[Feature.LUV] = luv_cd.describe(image)
    phash = imagehash.phash(image_src)
    imgObj["PHash"] = [x.item() for x in phash.hash.flatten()]

    # add labels
    labels = clf.predict(image).ravel()[::-1]
    probs = clf.predict_proba(image).ravel()[::-1]
    if not all(probs[i] >= probs[i + 1] for i in xrange(len(probs) - 1)):
        print("probs is not sorted")
        break
    label = []
    top_n_prob = 0
    length = len(labels)
    for i in range(length):
        tags = labels[i]
        prob = probs[i]
        top_n_prob += 1
        for tag in tags.split(","):
            label.append({"label": tag, "rank": top_n_prob, 'prob': probs[i].item()})
    imgObj["labels"] = label

    # add orb feature
    gray_image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    # Initiate STAR detector
    orb = cv2.ORB_create()
    # find the keypoints with ORB
    kp = orb.detect(gray_image, None)
    # compute the descriptors with ORB
    kp, des = orb.compute(gray_image, kp)
    orb_feature = PicklePoints.pickle_keypoints(kp, des)
    imgObj["ORB"] = orb_feature

    imgObj["md5"] = md5(imagePath)
    imgObj["CreateTime"] = datetime.datetime.utcnow()
    imgObj["UpdateTime"] = datetime.datetime.utcnow()
    if image_url is not None:
        imgObj["ImageUrl"] = args['url'].strip('/') + '/' + imgObj["ImageName"]
    imgObj["Path"] = "/" + imagePath
    # print(imgObj)
    collection.insert_one(imgObj)

    count += 1
    if count % 100 == 0:
        print(count)
        print(" --- %s seconds ---" % (time.time() - start_time))

print(count)
print("finish --- %s seconds ---" % (time.time() - start_time))
