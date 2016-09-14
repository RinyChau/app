import os
import sys
sys.path.append("app/dist/sklearn_theano-0.0.1-py2.7.egg")
import traceback

from flask import Flask, render_template, request, jsonify
from dao.imagedb import ImageDB
from pyimagesearch.colordescriptor import ColorDescriptor
from pyimagesearch.searcher import Searcher
from pyimagestore.imgManagement import ImgManagement
from skimage import io
from pyimagesearch.searcher import DistanceType
from pyimagesearch.colordescriptor import Feature
import sklearn_theano
import cv2
import thread
# create flask instance
app = Flask(__name__)

img_dir = os.path.join(os.path.dirname(__file__), 'static', 'image', "upload")
img_url_dir = os.path.join(os.path.dirname(__file__), 'static', 'image', "url")

# initialize the image descriptor
feature = Feature.LUV
distance_type = DistanceType.L1
cd = ColorDescriptor(feature=feature)
# initialize the searcher
searcher = Searcher(DistanceType.L1, feature)

# main route
@app.route('/')
def index():
    return render_template('index.html')
# search route
@app.route('/search', methods=['POST'])
def search():
    if request.method == "POST":
        result_array = []
        # get url
        image_url = request.form.get('url')
        image_file = request.files['img'] if 'img' in request.files else None

        try:
            # load the query image and describe it
            if image_file is not None and image_file.filename != '':
                results = searchImgByFile(image_file)
            else:
                results = searchImgByUrl(image_url)

            # loop over the results, displaying the score and image name
            for (score, url) in results:
                result_array.append(
                    {"image": str(url), "score": str(score)})

            # return success
            return jsonify(results=(result_array))
        except:
            print("*** app.search() takes error ***")
            print(sys.exc_info()[0])
            traceback.print_exc()
            print("*** app.search() takes error ***")
            # return error
            return jsonify({"sorry": "Sorry, no results! Please try again."}), 500


def searchImgByFile(image_file):
    imagePath = ImgManagement.saveFile(img_dir, image_file)
    imgMD5 = ImgManagement.getMD5(imagePath)
    imageItem = ImageDB.getItem({"md5": imgMD5})

    if imageItem is None:
        image = cv2.imread(imagePath)
        features = cd.describe(image)
        results = searcher.search(features)
        thread.start_new_thread(ImageDB.insert, (imgMD5, features, imagePath,))
    else:
        features = imageItem[feature]
        results = searcher.search(features)
        thread.start_new_thread(ImgManagement.deleteFile, (imagePath,))
    return results


def searchImgByUrl(image_url):
    query = io.imread(image_url)
    query = cv2.cvtColor(query, cv2.COLOR_RGB2BGR)
    features = cd.describe(query)
    results = searcher.search(features)
    thread.start_new_thread(ImgManagement.saveUrl, (image_url, img_url_dir,))
    return results

# run!
if __name__ == '__main__':
    app.run('0.0.0.0', port=80, debug=True)
