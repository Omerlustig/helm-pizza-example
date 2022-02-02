FROM node:slim
ARG USER=pizza
ARG GROUP=big
RUN groupadd $GROUP && useradd -u 7777 $USER -g $GROUP
WORKDIR /usr/src/app
COPY app/package.json ./
RUN npm install --only=prod
ADD app .
EXPOSE 3000
RUN chmod +x server.js && chown -R $USER:$GROUP .
USER $USER
CMD [ "node", "server.js" ]