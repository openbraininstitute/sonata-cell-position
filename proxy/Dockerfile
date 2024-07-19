FROM nginxinc/nginx-unprivileged:stable

COPY nginx.conf /etc/nginx/nginx.conf
COPY proxy_cache_common /etc/nginx/proxy_cache_common
COPY http.js /etc/nginx/http.js

CMD ["nginx", "-g", "daemon off;"]
