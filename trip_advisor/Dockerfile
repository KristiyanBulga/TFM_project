FROM public.ecr.aws/lambda/python:3.9 as build
RUN yum install -y unzip && \
    curl -Lo "/tmp/chromedriver.zip" "https://chromedriver.storage.googleapis.com/86.0.4240.22/chromedriver_linux64.zip" && \
    curl -Lo "/tmp/headless-chromium.zip" "https://github.com/adieuadieu/serverless-chrome/releases/download/v1.0.0-57/stable-headless-chromium-amazonlinux-2.zip" && \
    unzip /tmp/chromedriver.zip -d /opt/ && \
    unzip /tmp/headless-chromium.zip -d /opt/

FROM public.ecr.aws/lambda/python:3.9
RUN yum install atk cups-libs gtk3 libXcomposite alsa-lib \
    libXcursor libXdamage libXext libXi libXrandr libXScrnSaver \
    libXtst pango at-spi2-atk libXt xorg-x11-server-Xvfb \
    xorg-x11-xauth dbus-glib dbus-glib-devel -y
COPY ./requirements.txt .
RUN pip install --force-reinstall -r requirements.txt
COPY --from=build /opt/headless-chromium /opt/
COPY --from=build /opt/chromedriver /opt/
COPY ./functions ./functions
COPY ./utils ./utils