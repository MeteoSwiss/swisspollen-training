# syntax=docker/dockerfile:1
FROM tensorflow/tensorflow:latest-gpu-jupyter
ENV http_proxy http://proxy.meteoswiss.ch:8080
ENV https_proxy http://proxy.meteoswiss.ch:8080
RUN pip config set global.trusted-host "pypi.org files.pythonhosted.org pypi.python.org"

RUN pip3 install --upgrade pip

RUN rm /etc/apt/sources.list.d/cuda.list && rm /etc/apt/sources.list.d/tensorRT.list
RUN apt-get update --fix-missing
#RUN apt upgrade -y

RUN apt-get install python3.8-dev libmysqlclient-dev libgl1 ca-certificates -y

# install Python packages with pip
RUN pip3 install jupyterlab
RUN pip3 install clustimage \
		cython \
		dask \
		loky \
		matplotlib \
                myloginpath \
		mysqlclient \
		mysql-connector-python \
		numpy \
		opencv-python \
		pandas \
		scikit-image \
		scikit-learn \
		scipy \
		simplejson \
		SQLAlchemy \
		tensorflow-addons \
		tqdm
RUN pip3 install jupyterlab-topbar \
		jupyter-resource-usage \
		jupyterlab_execute_time \
		jupyterlab-system-monitor \
		jupyterlab-horizon-theme \
                jupyterlab_nvdashboard

# install more requirements
#ADD requirements.txt tmp/
#RUN pip3 install -r tmp/requirements.txt

# install local requirements
ADD dependencies/CharPyLS-master/ tmp/CharPyLS-master/
RUN pip3 install tmp/CharPyLS-master/

ADD dependencies/poleno-db-interface/ tmp/poleno-db-interface/
RUN pip3 install tmp/poleno-db-interface/

ADD dependencies/poleno-ml/ tmp/poleno-ml/
RUN pip3 install tmp/poleno-ml/

# add config file
ADD config/.mylogin.cnf .

# setup jupyterlab user-preferences, theme, and settings
ADD config/plugin.jupyterlab-settings .
RUN mkdir -p /root/.jupyter/lab/user-settings/@jupyterlab/fileeditor-extension/
RUN mv plugin.jupyterlab-settings /root/.jupyter/lab/user-settings/@jupyterlab/fileeditor-extension/plugin.jupyterlab-settings

ADD config/themes.jupyterlab-settings .
RUN mkdir -p /root/.jupyter/lab/user-settings/\@jupyterlab/apputils-extension/
RUN mv themes.jupyterlab-settings /root/.jupyter/lab/user-settings/\@jupyterlab/apputils-extension/themes.jupyterlab-settings

ADD config/tracker.jupyterlab-settings .
#RUN jupyter-lab --generate-config # to generate the default config file of jupyter lab
RUN mkdir -p /root/.jupyter/lab/user-settings/\@jupyterlab/notebook-extension/
RUN mv tracker.jupyterlab-settings /root/.jupyter/lab/user-settings/\@jupyterlab/notebook-extension/tracker.jupyterlab-settings

# start jupyter lab at startup
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--allow-root", "--LabApp.token=''"]

