
import multiprocessing
import queue
import pandas as pd

class BackgroundGenerator(multiprocessing.Process):
    def __init__(self, dataset, mysqlSettings, prefetch=1, chunksize=100, autoRestart=True, reserveFirst=False, prepareFunc=None, with_fl=False):
        multiprocessing.Process.__init__(self)
        self.prepareFunc = prepareFunc

        self.with_fl = with_fl
        self.dataset = dataset
        self.reserveFirst = reserveFirst
        self.first = multiprocessing.Queue(1)
        self.chunksize = chunksize
        self.mysqlSettings = mysqlSettings
        self.autoRestart = autoRestart
        self.queue = multiprocessing.Queue(prefetch)
        
        self.daemon = True
        self.start()
    
    def getFirst(self):
        #if not self.reserveFirst:
        #    print("Warning: First is not reserved!")
        #print("Fetching first data...")
        ret = self.first.get()
        self.first.put_nowait(ret)
        #print("Data ready")
        return ret

    def run(self):
        from mysqlInterface import MySqlConnector
        dataDB = MySqlConnector(**self.mysqlSettings)
        if self.with_fl:
            #print("Setting query with fluorescence!")
            self.query = dataDB.getDatasetDFQueryFLFast(self.dataset)
        else:
            self.query = dataDB.getDatasetDFQuery(self.dataset)

        self.generator = dbBatchGenerator(self.query, self.mysqlSettings, chunksize=self.chunksize, prepareFunc=self.prepareFunc)
        while(True):
            isFirst=True
            for item in self.generator:
                if isFirst:
                    isFirst = False
                    try:
                        self.first.put_nowait(item)
                    except queue.Full:
                        pass # Ignor if it is full.
                    if not self.reserveFirst:
                        self.queue.put(item)
                else:
                    self.queue.put(item)
            if self.autoRestart:
                #print("Restarting iterator", flush=True)
                self.generator = dbBatchGenerator(self.query, self.mysqlSettings, chunksize=self.chunksize, prepareFunc=self.prepareFunc)
            else:
                self.queue.put(None)
                break
    
    def __iter__(self):
        return self

    def __next__(self):
            #print("fetching data")
            next_item = self.queue.get() #NB : stuck here
            #print("done")
            if next_item is None:
                 raise StopIteration
            return next_item

def dbBatchGenerator(query, mysqlSettings, chunksize, prepareFunc=None):
    i = 0
    res = query.limit(chunksize).all()
    while res is not None and len(res) > 0:
        i += 1
        #print("next batch elements: ", len(res), flush=True)
        if prepareFunc is None:
            ret = pd.DataFrame(res)
            yield ret
        else:
            ret = prepareFunc(pd.DataFrame(res))
            yield ret
        res = query.limit(chunksize).offset(i*chunksize).all()
    
    #print("Iterator Empty!!", flush=True)

# def dbBatchGenerator2(query, mysqlSettings, chunksize, prepareFunc=None, **kwargs):
#     i = 0
#     res = query(**kwargs, limit=chunksize).all()
#     while res is not None and len(res) > 0:
#         i += 1
#         print("next batch elements: ", len(res), flush=True)
#         if prepareFunc is None:
#             ret = pd.DataFrame(res)
#             yield ret
#         else:
#             ret = prepareFunc(pd.DataFrame(res))
#             yield ret
#         res = query(**kwargs, limit=chunksize, offset=i*chunksize).all()
    
#     print("Iterator Empty!!", flush=True)

