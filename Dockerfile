FROM node:slim
WORKDIR /usr/src/app
COPY app/package.json ./
RUN npm install --only=prod
ADD app .
EXPOSE 3000
CMD [ "node", "server.js" ]
#change user root
#delete leftovers