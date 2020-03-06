FROM ubuntu:18.04

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
                        firefox xfonts-100dpi git python-pip && \
                        rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# DO NOT install nibabel (so MEICA uses local libraries)
COPY requirements.txt ./requirements.txt
RUN pip install update pip && pip install -r requirements.txt && rm -rf /root/.cache/pip

# Install AFNI binaries                  
RUN ln -s /usr/lib/x86_64-linux-gnu/libgsl.so.23 /usr/lib/x86_64-linux-gnu/libgsl.so.19
RUN cd && curl -O https://afni.nimh.nih.gov/pub/dist/bin/linux_ubuntu_16_64/@update.afni.binaries && \
    tcsh @update.afni.binaries -package linux_ubuntu_16_64  -do_extras

ENV DEBIAN_FRONTEND=noninteractive
ENV HOME="/root"

ENV PATH="${PATH}:${HOME}/abin"

# Make afni/suma profiles
RUN cp $HOME/abin/AFNI.afnirc $HOME/.afnirc && suma -update_env

# May or may not actually use this
RUN git clone https://github.com/ME-ICA/me-ica.git
COPY run /flywheel/v0/run
COPY run_meica.py /flywheel/v0/run_meica.py