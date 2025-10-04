FROM nginx:1.27-alpine
WORKDIR /usr/share/nginx/html
# Copy everything from ./web into the Nginx html directory
COPY web/ .
