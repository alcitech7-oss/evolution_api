FROM node:18-alpine

WORKDIR /app

RUN npm install -g @evolutionapi/api

EXPOSE 8080

CMD ["evolutionapi"]
