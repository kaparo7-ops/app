FROM nginx:1.27-alpine
WORKDIR /usr/share/nginx/html
COPY index.html ./
COPY tenders.html ./
# استخدم إعدادات Nginx الجديدة
COPY nginx.conf /etc/nginx/nginx.conf
