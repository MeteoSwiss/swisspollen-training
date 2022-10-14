import cv2
import pandas as pd
from typing import Tuple
from ImageHelper import imageFromBlob
import numpy as np
import matplotlib.pyplot as plt

def load_blob(img0, img1):
    def process_imgs(imgs):
        # convert image from blob
        # convert to numpy matrix
        # normalize
        # convert to 2d list
        return imgs.apply(imageFromBlob)\
                   .apply(lambda x: np.array(x, dtype=float) / (2**16-1))
    img0, img1 = process_imgs(img0), process_imgs(img1)
    return img0, img1

def process_waves(img0, img1):
    def waves_remover(img:np.ndarray, plot:bool=False):
        img = (img*255).astype(np.uint8)
        blurred = cv2.GaussianBlur(img, (5, 5), 0)
        _, mask = cv2.threshold(blurred, 0, 1, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        clean = img * ~(mask).astype(bool)

        # crop
        ## argwhere will give you the coordinates of every non-zero point
        true_points = np.argwhere(clean)
        ## take the smallest points and use them as the top left of your crop
        top_left = true_points.min(axis=0)
        ## take the largest points and use them as the bottom right of your crop
        bottom_right = true_points.max(axis=0)
        cropped = clean[top_left[0]:bottom_right[0]+1,  # plus 1 because slice isn't
                        top_left[1]:bottom_right[1]+1]  # inclusive

        if plot:
            _, (ax1,ax2,ax3,ax4,ax5) = plt.subplots(1,5)
            ax1.imshow(img)
            ax2.imshow(blurred)
            ax3.imshow(mask)
            ax4.imshow(clean)
            ax5.imshow(cropped)
            plt.show()
        return clean

    img0 = img0.apply(waves_remover)
    img1 = img1.apply(waves_remover)
    return img0, img1

def filter_blur(img0: pd.Series, img1: pd.Series, T: int = .0014) -> Tuple[pd.Series, pd.Series]:
    df = pd.DataFrame([img0, img1]).T
    # if the variance of the Laplacian is < T, image is considered blurry
    mask_to_delete = df[['img0', 'img1']].apply(
        lambda x: cv2.Laplacian(x[0], cv2.CV_64F).var() < T or cv2.Laplacian(x[1], cv2.CV_64F).var() < T,
        axis=1
    )
    return df.loc[~mask_to_delete].img0, df.loc[~mask_to_delete].img1

def filter_crop(img0: pd.Series, img1: pd.Series, T: float = .0001, BT: float = .85) -> Tuple[pd.Series, pd.Series]:
    try:
        holo0 = img0.iloc[0]
        border = [0,holo0.shape[0]-1]#,1,holo0.shape[0]-2]
        mask = np.array([
            [1. if i in border or j in border else 0. for j in range(holo0.shape[1])]
             for i in range(holo0.shape[0])
        ])
        df = pd.DataFrame([img0, img1]).T
        scores = df[['img0', 'img1']].apply(
            lambda x: (((x[0]<BT)*mask).sum() / mask.sum(), 
                       ((x[1]<BT)*mask).sum() / mask.sum()), 
            axis=1
        )
        uuids_to_delete = scores.apply(lambda x: x[0] > T or x[1] > T)
        return df.loc[~uuids_to_delete].img0, df.loc[~uuids_to_delete].img1
    except: # if img.size is 0
        return img0, img1