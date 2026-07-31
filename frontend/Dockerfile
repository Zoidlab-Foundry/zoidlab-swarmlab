FROM node:20-alpine
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build
ENV PORT=3707
EXPOSE 3707
CMD ["npm", "run", "start"]
