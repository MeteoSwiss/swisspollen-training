"""
Author: Yanick Zeder (yanick.zeder@swisens.ch)
Date: 11.02.2019
"""

import mysql.connector as connector
import mysql.connector.pooling
from uuid import getnode as get_mac
from uuid import uuid4
from ImageHelper import blobFromImage, imageFromBlob
import time
import json
import logging
import threading

from sqlalchemy.ext.automap import automap_base, generate_relationship
from sqlalchemy.orm import Session, aliased, scoped_session, sessionmaker, relationship
from sqlalchemy.sql import text, func, and_, or_
from sqlalchemy.types import LargeBinary as Binary
from sqlalchemy.dialects.mysql import insert
from sqlalchemy import create_engine, desc, asc, Table, Column, ForeignKey

import numpy as np

# Dataset Status Strings
NEW_STATUS = "New"
DO_EXPORT_STATUS = "DoExport"
EXPORTING_STATUS = "Exporting"
EXPORT_DONE_STATUS = "ExportDone"

class MySqlConnector(object):
    """
    Class to connect to the Swisens mysql database
    """


    ##### Helpers
    def _dumpAsJson(self, obj):
        """
        Helper to dump a object as json. Supports numpy objects.
        """
        return json.dumps(obj, separators=(',', ':'), cls=NpEncoder)
        
    def writChangesToDB(self):
        self.session.commit()
    
    def _gen_relationship(self, base, direction, return_fn, attrname, local_cls, referred_cls, **kw):
        if local_cls.__name__ == "EventDataset" and referred_cls.__name__ == "Event":
            attrname = "_EventsInEventDatasets"
        elif local_cls.__name__ == "Event" and referred_cls.__name__ == "EventDataset":
            attrname = "_EventDatasetsOfEvent"
        else:
            attrname = attrname+'_ref'+str(self.refNums)
            self.refNums += 1
        return generate_relationship(base, direction, return_fn, attrname, local_cls, referred_cls, **kw)

    def _name_for_collection_relationship(self, base, local_cls, referred_cls, constraint):
        pass

    def __init__(self, user, password, host, database, port = 3307, deviceId=None, sshServer=None):
        """
        Initializes the connector configuration and creating a connection pool for the mysql database.
        """
        self.config = {
            'user': user,
            'password': password,
            'host': host if sshServer is None else "127.0.0.1",
            'port': port if sshServer is None else str(sshServer.local_bind_port),
            'database': database,
            'raise_on_warnings': True,
            'auth_plugin': 'mysql_native_password'
        }

        ######### Preparing the database connection
        self.refNums = 0
        self.Base = automap_base()

        ## Define some classes which have many to many relations:
        event_eventdataset_table = Table('EventsInEventDataset', self.Base.metadata,
            Column('Measurement_id', Binary(16), ForeignKey('Event.id')),
            Column('MeasurementDataset_id', Binary(16), ForeignKey('EventDataset.id'))
        )

        class EventDataset(self.Base):
            __tablename__ = "EventDataset"
            EventsInEventDatasets = relationship("Event", secondary=event_eventdataset_table)

        self.event_eventdataset_table = event_eventdataset_table
        self.TEventDataset = EventDataset

        # pool-pre-pining should eliminate "MySQL Database has gone" error
        self.engine = create_engine(
            f"mysql+mysqldb://{user}:{password}@{host}:{port}/{database}", 
            pool_pre_ping=True, 
            json_serializer=self._dumpAsJson,
            execution_options={"stream_results":True}
        )#, echo=True)
        self.session = scoped_session(sessionmaker(bind=self.engine))
        self.Base.prepare(self.engine, reflect=True, generate_relationship=self._gen_relationship)

        if deviceId is None:
            result = self.session.execute(text("SELECT @@server_id")).first()
            if result is None: raise Exception("Error: No server id found for this mysql server.")
            self._deviceId = result[0]
        
        ######### Reflect the database structure to local objects
        
        #### DeviceManagement

        self.TDevice = self.Base.classes.Device
        self.TDevicePublicKey = self.Base.classes.DevicePublicKey

        #### User Management

        self.TRestApiUsers = self.Base.classes.RestApiUsers
        self.TDeviceAccess = self.Base.classes.DeviceAccess

        #### Logging

        self.TSystemDataLog = self.Base.classes.SystemDataLog

        #### Raw Particle Data

        self.TEvent = self.Base.classes.Event
        self.TFLData = self.Base.classes.FlData
        self.TFlAdcDump = self.Base.classes.FlAdcDump
        self.TPolData = self.Base.classes.PolData
        self.TImageData = self.Base.classes.ImageData

        #### Classification

        self.TClassification = self.Base.classes.Classification

        #### Computed Particle Properties

        self.TParticleProperties = self.Base.classes.ParticleProperties
        self.TImageAnalysis = self.Base.classes.ImageAnalysis

        #### Datasets

        #self.TEventDataset = self.Base.classes.EventDataset

        #### N to M relations  ==> Handled directly by sqlalchemy.

        #self.TUserClassifications = self.Base.classes.UserClassifications
        #self.TDatasetDownloads = self.Base.classes.DatasetDownloads
        #self.TEventsInEventDataset = self.Base.classes.EventsInEventDataset

        logging.info("MySQL interface initialisation complete.")

    def getDatasetDFQuery(self, datasetID, offset=None, limit=None):

        # Build the event query
        eventAlias = aliased(self.TEvent)
        img0Alias = aliased(self.TImageData)
        img1Alias = aliased(self.TImageData)

        reQuery = self.session.query(
            img0Alias.imageDataReconstructedBlob.label("img0"),
            img1Alias.imageDataReconstructedBlob.label("img1")
        ).select_from(
            self.TEventDataset
        ).join(
            eventAlias,
            self.TEventDataset.EventsInEventDatasets
        ).filter(
            self.TEventDataset.id == func.uuid_to_bin(datasetID)
        ).join(
            img0Alias,
            and_(
                img0Alias.Event_id == eventAlias.id,
                img0Alias.id == "0")
        ).join(
            img1Alias,
            and_(
                img1Alias.Event_id == eventAlias.id,
                img1Alias.id == "1")
        )
        # Filter is used to reference external event alias to internal one.
    
        if limit is not None:
            reQuery = reQuery.limit(limit)
        if offset is not None:
            reQuery = reQuery.offset(offset)

        return reQuery

    def getDatasetDFQueryFL(self, datasetID, offset=None, limit=None):

        # Build the event query
        eventAlias = aliased(self.TEvent)
        img0Alias = aliased(self.TImageData)
        img1Alias = aliased(self.TImageData)
        flAlias = aliased(self.TFLData)

        reQuery = self.session.query(
            img0Alias.imageDataReconstructedBlob.label("img0"),
            img1Alias.imageDataReconstructedBlob.label("img1"),
            func.json_objectagg(flAlias.configNum, flAlias.corrMag).label("corrMag"),
            func.json_objectagg(flAlias.configNum, flAlias.corrPha).label("corrPha"),
            func.json_objectagg(flAlias.configNum, flAlias.avg).label("avg")
        ).select_from(
            self.TEventDataset
        ).join(
            eventAlias,
            self.TEventDataset.EventsInEventDatasets
        ).filter(
            self.TEventDataset.id == func.uuid_to_bin(datasetID)
        ).join(
            img0Alias,
            and_(
                img0Alias.Event_id == eventAlias.id,
                img0Alias.id == "0")
        ).join(
            img1Alias,
            and_(
                img1Alias.Event_id == eventAlias.id,
                img1Alias.id == "1")
        ).join(
            flAlias,
            flAlias.Event_id == eventAlias.id
        ).group_by(
            eventAlias.id
        )
        # Filter is used to reference external event alias to internal one.
    
        if limit is not None:
            reQuery = reQuery.limit(limit)
        if offset is not None:
            reQuery = reQuery.offset(offset)

        return reQuery

    def getDatasetDFQueryFLFast(self, datasetID, offset=None, limit=None):

        # Build the event query
        eventAlias = aliased(self.TEvent)
        img0Alias = aliased(self.TImageData)
        img1Alias = aliased(self.TImageData)
        flAlias = aliased(self.TFLData)

        subq = self.session.query(
            self.event_eventdataset_table.c.Measurement_id.label("id")
        ).filter(
            self.event_eventdataset_table.c.MeasurementDataset_id == func.uuid_to_bin(datasetID)
        ).subquery()

        reQuery = self.session.query(
            img0Alias.imageDataReconstructedBlob.label("img0"),
            img1Alias.imageDataReconstructedBlob.label("img1"),
            func.json_objectagg(flAlias.configNum, flAlias.corrMag).label("corrMag"),
            func.json_objectagg(flAlias.configNum, flAlias.corrPha).label("corrPha"),
            func.json_objectagg(flAlias.configNum, flAlias.avg).label("avg")
        ).select_from(
            subq
        ).join(
            img0Alias,
            and_(
                img0Alias.Event_id == subq.c.id,
                img0Alias.id == "0")
        ).join(
            img1Alias,
            and_(
                img1Alias.Event_id ==  subq.c.id,
                img1Alias.id == "1")
        ).join(
            flAlias,
            flAlias.Event_id == subq.c.id
        ).group_by(
             subq.c.id
        )
        # Filter is used to reference external event alias to internal one.
    
        if limit is not None:
            reQuery = reQuery.limit(limit)
        if offset is not None:
            reQuery = reQuery.offset(offset)

        return reQuery

    def getTimeseriesDFQueryFLFast(self, deviceId, from_time, to_time, offset=None, limit=None):

        # Build the event query
        eventAlias = aliased(self.TEvent)
        img0Alias = aliased(self.TImageData)
        img1Alias = aliased(self.TImageData)
        flAlias = aliased(self.TFLData)
        imgPropAlias0 = aliased(self.TImageAnalysis)
        imgPropAlias1 = aliased(self.TImageAnalysis)

        subq = self.session.query(
            eventAlias.id.label("id"),
            eventAlias.timestamp.label("timestamp")
        ).filter(
            eventAlias.Device_idDevice == deviceId
        )

        if from_time is not None:
            subq = subq.filter(
                eventAlias.timestamp > from_time
            )
        if to_time is not None:
            subq = subq.filter(
                eventAlias.timestamp < to_time
            )

        if limit is not None:
            subq = subq.limit(limit)
        if offset is not None:
            subq = subq.offset(offset)
        
        subq = subq.subquery()

        reQuery = self.session.query(
            # Meta information
            func.bin_to_uuid(subq.c.id).label("id"),
            subq.c.timestamp.label("timestamp"),

            # Images
            func.ANY_VALUE(img0Alias.imageDataReconstructedBlob).label("img0"),
            func.ANY_VALUE(img1Alias.imageDataReconstructedBlob).label("img1"),

            # FL Data
            func.json_objectagg(flAlias.configNum, flAlias.corrMag).label("corrMag"),
            func.json_objectagg(flAlias.configNum, flAlias.corrPha).label("corrPha"),
            func.json_objectagg(flAlias.configNum, flAlias.avg).label("avg"),

            # Image Properties
            func.ANY_VALUE(imgPropAlias0.particleArea).label("particleArea_0"),
            func.ANY_VALUE(imgPropAlias0.particleSolidity).label("particleSolidity_0"),
            func.ANY_VALUE(imgPropAlias0.particleEccentricity).label("particleEccentricity_0"),
            func.ANY_VALUE(imgPropAlias0.particleMinorAxis).label("particleMinorAxis_0"),
            func.ANY_VALUE(imgPropAlias0.particleMajorAxis).label("particleMajorAxis_0"),
            func.ANY_VALUE(imgPropAlias0.particlePerimeter).label("particlePerimeter_0"),
            func.ANY_VALUE(imgPropAlias0.particleMinIntensity).label("particleMinIntensity_0"),
            func.ANY_VALUE(imgPropAlias0.particleMeanIntensity).label("particleMeanIntensity_0"),
            func.ANY_VALUE(imgPropAlias0.particleMaxIntensity).label("particleMaxIntensity_0"),
            func.ANY_VALUE(imgPropAlias0.particleMaxSolidity).label("particleMaxSolidity_0"),
            func.ANY_VALUE(imgPropAlias0.particleCoordinates).label("particleCoordinates_0"),

            func.ANY_VALUE(imgPropAlias1.particleArea).label("particleArea_1"),
            func.ANY_VALUE(imgPropAlias1.particleSolidity).label("particleSolidity_1"),
            func.ANY_VALUE(imgPropAlias1.particleEccentricity).label("particleEccentricity_1"),
            func.ANY_VALUE(imgPropAlias1.particleMinorAxis).label("particleMinorAxis_1"),
            func.ANY_VALUE(imgPropAlias1.particleMajorAxis).label("particleMajorAxis_1"),
            func.ANY_VALUE(imgPropAlias1.particlePerimeter).label("particlePerimeter_1"),
            func.ANY_VALUE(imgPropAlias1.particleMinIntensity).label("particleMinIntensity"),
            func.ANY_VALUE(imgPropAlias1.particleMeanIntensity).label("particleMeanIntensity_1"),
            func.ANY_VALUE(imgPropAlias1.particleMaxIntensity).label("particleMaxIntensity_1"),
            func.ANY_VALUE(imgPropAlias1.particleMaxSolidity).label("particleMaxSolidity_1"),
            func.ANY_VALUE(imgPropAlias1.particleCoordinates).label("particleCoordinates_1"),
        ).select_from(
            subq
        ).join(
            img0Alias,
            and_(
                img0Alias.Event_id == subq.c.id,
                img0Alias.id == "0")
        ).join(
            img1Alias,
            and_(
                img1Alias.Event_id ==  subq.c.id,
                img1Alias.id == "1")
        ).join(
            flAlias,
            flAlias.Event_id == subq.c.id
        ).join(
            imgPropAlias0,
            and_(
                imgPropAlias0.ImageData_Event_id == subq.c.id,
                imgPropAlias0.ImageData_id == "0"
            )
        ).join(
            imgPropAlias1,
            and_(
                imgPropAlias1.ImageData_Event_id == subq.c.id,
                imgPropAlias1.ImageData_id == "1"
            )
        ).group_by(
            subq.c.id
        )

        return reQuery

class NpEncoder(json.JSONEncoder):
  """
  Class which allows numpy objects to be json serialized.
  """
  def default(self, obj):
    if isinstance(obj, np.integer):
      return int(obj)
    elif isinstance(obj, np.floating):
      return float(obj)
    elif isinstance(obj, np.ndarray):
      return obj.tolist()
    else:
      return super(NpEncoder, self).default(obj)
