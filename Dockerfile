FROM node:slim
ARG USER=pizza
ARG GROUP=big
RUN groupadd $GROUP && useradd -u 7777 $USER -g $GROUP
WORKDIR /usr/src/app
COPY pizza-express-master/package.json ./
RUN npm install --only=prod
COPY pizza-express-master .
EXPOSE 3000
RUN chmod +x server.js && chown -R $USER:$GROUP .
USER $USER
CMD [ "node", "server.js" ]