# syntax=docker/dockerfile:1
FROM tensorflow/tensorflow:latest-gpu-jupyter
ENV http_proxy http://proxy.meteoswiss.ch:8080
ENV https_proxy http://proxy.meteoswiss.ch:8080
RUN pip config set global.trusted-host "pypi.org files.pythonhosted.org pypi.python.org"

#RUN apt-get update && apt-get upgrade
RUN pip3 install --upgrade pip

RUN apt-get install python3.8-dev libmysqlclient-dev libgl1 -y

# install Python packages with pip
RUN pip3 install clustimage \
		cython \
		jupyterlab \
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
		SQLAlchemy \
		tqdm \
#		jupyterlab-topbar \
		jupyter-resource-usage \
		jupyterlab_execute_time \
		jupyterlab-system-monitor \
		jupyterlab-horizon-theme

# install more requirements
#ADD requirements.txt .
#RUN pip3 install -r requirements.txt
ADD dependencies/CharPyLS-master/ CharPyLS-master/
RUN pip3 install -e CharPyLS-master/

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

