FROM ubuntu:18.04


#################################################################################################
# Afni installation as officially recommended for consistency: 
# https://afni.nimh.nih.gov/pub/dist/doc/htmldoc/background_install/install_instructs/steps_linux_ubuntu18.html#install-afni-binaries


# Install dependencies
RUN apt-get update && apt-get install -y software-properties-common && \
                        add-apt-repository universe && \
                        apt-get update && \
                        apt-get install -y tcsh xfonts-base python-qt4       \
                        gsl-bin netpbm gnome-tweak-tool   \
                        libjpeg62 xvfb xterm vim curl     \
                        gedit evince eog                  \
                        libglu1-mesa-dev libglw1-mesa     \
                        libxm4 build-essential            \
                        libcurl4-openssl-dev libxml2-dev  \
                        libssl-dev libgfortran3           \
                        gnome-terminal nautilus           \
                        gnome-icon-theme-symbolic         \
                        firefox xfonts-100dpi git python-pip python3-pip && \
                        rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# DO NOT install nibabel (so MEICA uses local libraries)
COPY requirements.txt ./requirements.txt

# These requirements are for the execution of the run.py python code
RUN pip3 install update pip && pip3 install -r requirements.txt && rm -rf /root/.cache/pip3
# These requirements are for the execution of AFNI's python code
RUN pip install update pip && pip install -r requirements.txt && rm -rf /root/.cache/pip

# Make a symbolic link for the specific version of GSL included in this version of Ubuntu.                
RUN ln -s /usr/lib/x86_64-linux-gnu/libgsl.so.23 /usr/lib/x86_64-linux-gnu/libgsl.so.19

# Install afni binaries:
# Download and unpack the current binaries in your $HOME directory
# (and yes, that @update* program works even, even though the link 
# has “ubuntu_16” in it); set the AFNI binary directory name to $HOME/abin/;
# and add that location to the $PATH in both ~/.cshrc and ~/.bashrc

RUN cd && curl -O https://afni.nimh.nih.gov/pub/dist/bin/linux_ubuntu_16_64/@update.afni.binaries && \
    tcsh @update.afni.binaries -package linux_ubuntu_16_64  -do_extras
    
# Set DEBIAN_FRONTEND to noninteractive so afni doesn't ask for keyboard input
ENV DEBIAN_FRONTEND=noninteractive
ENV HOME="/root"

ENV PATH="${PATH}:${HOME}/abin"

# Make afni/suma profiles
# Set up vanilla-mode environment variables for AFNI and SUMA.
RUN cp $HOME/abin/AFNI.afnirc $HOME/.afnirc && suma -update_env

# END afni recommended Installation
#################################################################################################

# May or may not actually use this
#RUN git clone https://github.com/ME-ICA/me-ica.git
COPY run.py /flywheel/v0/run.py
COPY afni_utils.py /flywheel/v0/afni_utils.py

############################
# ENV preservation for Flywheel Engine
RUN python -c 'import os, json; f = open("/tmp/gear_environ.json", "w"); json.dump(dict(os.environ), f)'