import io
from PIL import Image
import numpy as np
import jpeg_ls as jls
import jpeg_ls.CharLS
from jpeg_ls import data_io
import sys
import timeit
from functools import lru_cache

def blobFromImage(numpyImageArray, debug=False):
    """
    Creates a in memory file jpeg-ls object and returns the binary of the image.
    Args:
        numpyImageArray (np.ndarray): Image to convert to jpeg-ls blob
    """
    if debug: print('compressing image..')

    # check datatype and convert if needed
    if numpyImageArray.dtype == np.float or numpyImageArray.dtype == np.float32 or numpyImageArray.dtype == np.float64:
        numpyImageArray = ( np.clip(numpyImageArray, 0, 1) * (2 ** 16 - 1) ).astype(np.uint16)
    
    output = io.BytesIO()
    image = jls.CharLS.encode(numpyImageArray)
    output.write(image)
    output.seek(0)
    blob = output.read()

    if debug:
        print('Size before compression: ' + str(sys.getsizeof(numpyImageArray)))
        print('Size after compression: ' + str(sys.getsizeof(blob)))
        print('ratio: ' + str(sys.getsizeof(blob)/sys.getsizeof(numpyImageArray)))
    return blob

def imageFromBlob(blob, debug=False):
    compressedImage = np.frombuffer(blob, dtype=np.uint8)
    image = jls.CharLS.decode(compressedImage)
    return image

def inMemoryFilePointer(image, imageFormat='jpeg'):
    """
    converts np.array to image object and returns an in-memory file pointer
    image: The image numpy array
    format: File format like jpeg or png
    """
    output = io.BytesIO()
    image = Image.fromarray(image)
    image.save(output, format=imageFormat)
    return output

def inMemoryFilePointerJPEG(image):
    return inMemoryFilePointer(image, 'jpeg')

def test_performance():
    numpyRandomImage = np.ones((200, 200), dtype=np.uint16)
    blob = blobFromImage(numpyRandomImage, debug=False)
    image = imageFromBlob(blob, debug=False)

if __name__ == '__main__':
    pass