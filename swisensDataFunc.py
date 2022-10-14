from backgroundGenerator import BackgroundGenerator
from ImageHelper import imageFromBlob
import numpy as np
import pandas as pd
import tensorflow as tf
from typing import Callable
import warnings

# Yanick's comment on how he did this ? https://stackoverflow.com/questions/41276972/read-mysql-database-in-tensorflow/60717965#60717965

def init_sets(datasetList: list, batchsize: int, chunksize: int, chunkPrefetch: int, mysqlSettings: dict, target_ids_mapping: dict, num_classes: int, img_preprocessing: Callable):
    # init training set
    itList = []
    for i, (label, _, dataset) in enumerate(datasetList):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            itList.append(
                BackgroundGenerator(
                    dataset,
                    prefetch=chunkPrefetch,
                    mysqlSettings=mysqlSettings, 
                    chunksize=chunksize,
                    reserveFirst=False,
                    with_fl=False,
                    prepareFunc=getPrepareFunc(img_preprocessing, with_fluorescence=False, label=target_ids_mapping[i])
                )
            )
    #trainingSet = get_train(itList, batchsize, num_classes)
    testset = get_test(itList, batchsize, num_classes, testsetMode='fromFirstChunk')
    return itList, testset

def get_train(itList, batchsize, num_classes):
    return datasetFromItList(itList=itList, batchsize=batchsize, num_classes=num_classes)

def get_test(itList, batchsize, num_classes, testsetMode='fromFirstChunk'):
    print("Building testset", flush=True)
    return datasetFromItList(itList=itList, batchsize=batchsize, num_classes=num_classes, first=True)

# swisens func
# preprocessing of images/fluorescence data
def getPrepareFunc(img_preprocessing, label, with_fluorescence=False):
    def processFLColumn(x, mapping=lambda x: x):
        x = json.loads(x)
        result = []
        i = 0
        while str(i) in x:
            result.extend(x[str(i)])
            i += 1
        result = [mapping(a) for a in result]
        return result
    def processDf(df):
        img0, img1 = img_preprocessing(df.img0, df.img1)
        df = df.loc[df.index.isin(img0.index)]
        df.img0 = img0
        df.img1 = img1
        if with_fluorescence:
            df["avg"] = df["avg"].apply(
                processFLColumn,
                mapping = lambda x: x/0.5
            )
            df["corrPha"] = df["corrPha"].apply(
                processFLColumn,
                mapping = lambda x: x/np.pi
            )
            df["corrMag"] = df["corrMag"].apply(
                processFLColumn,
                mapping = lambda x: x/0.5
            )
        df["label"] = label
        return df
    return processDf

# swisens func
# create TF dataset
def datasetFromItList(itList, num_classes, batchsize, first=False, with_fluorescence=False):
    df = None
    for i, it in enumerate(itList):
        if first:
            dfTmp : pd.DataFrame = it.getFirst()
        else:
            dfTmp : pd.DataFrame = next(it)
        if df is None:
            df = dfTmp
        else:
            #df = df.append(dfTmp)
            df = pd.concat([df, dfTmp])
    #print("Randomizing the sample in the set", flush=True)
    df = df.sample(frac=1).reset_index(drop=True) # NB df contains 12000 events(=250[events/(chunk*dataset)]*48[datasets])
    #print("Building TF-Dataset", flush=True)
    if with_fluorescence:
        datasetData = tf.data.Dataset.from_tensor_slices(
            (
                np.array(df["img0"].to_list()).reshape((len(df),200,200,1)), 
                np.array(df["img1"].to_list()).reshape((len(df),200,200,1)),
                np.array(df["avg"].to_list()).reshape((len(df), n_fl_configs*6, 1)),
                np.array(df["corrPha"].to_list()).reshape((len(df), n_fl_configs*6, 1)),
                np.array(df["corrMag"].to_list()).reshape((len(df), n_fl_configs*6, 1))
            ))
    else:
        datasetData = tf.data.Dataset.from_tensor_slices((
            np.array(df["img0"].to_list()).reshape((len(df),200,200,1)), 
            np.array(df["img1"].to_list()).reshape((len(df),200,200,1))
        ))
    datasetLabels = tf.data.Dataset.from_tensor_slices((
        tf.one_hot(df["label"].values, num_classes)
    ))

    dataset = tf.data.Dataset.zip((datasetData, datasetLabels)).batch(batchsize) #NB dataset into batch
    return dataset