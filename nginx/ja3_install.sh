#!/usr/bin/env bash
# Build nginx with JA3 + JA4 TLS fingerprinting support.
#
# OPTIONAL — AI Abyss works without this. The only feature you lose is
# TLS fingerprint classification. All other signals (UA, IP, behaviour,
# headers) work standalone.
#
# This compiles nginx from source with the ngx_ssl_fingerprint_module
# which provides JA3, JA4, and HTTP/2 fingerprint variables.
#
# Run on Ubuntu/Debian. After installation:
#   1. Uncomment ssl_ja3/ssl_ja4 directives in nginx.conf
#   2. Set: proxy_set_header X-JA3-Hash $ssl_ja3_hash;
#
# Module: https://github.com/HanadaLee/ngx_ssl_fingerprint_module
# (supports JA3 + JA4 + HTTP/2 fingerprinting)

set -euo pipefail

NGINX_VERSION="1.28.2"
FINGERPRINT_MODULE_REPO="https://github.com/HanadaLee/ngx_ssl_fingerprint_module.git"
BUILD_DIR="/tmp/nginx-fingerprint-build"

echo "==> Installing build dependencies"
apt-get update
apt-get install -y \
    build-essential \
    libpcre2-dev \
    zlib1g-dev \
    libssl-dev \
    git \
    wget

echo "==> Creating build directory"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

echo "==> Downloading nginx ${NGINX_VERSION}"
wget -q "https://nginx.org/download/nginx-${NGINX_VERSION}.tar.gz"
tar xzf "nginx-${NGINX_VERSION}.tar.gz"

echo "==> Cloning TLS fingerprint module (JA3 + JA4)"
git clone "$FINGERPRINT_MODULE_REPO" ngx_ssl_fingerprint_module

echo "==> Configuring nginx with fingerprint module"
cd "nginx-${NGINX_VERSION}"
./configure \
    --prefix=/etc/nginx \
    --sbin-path=/usr/sbin/nginx \
    --conf-path=/etc/nginx/nginx.conf \
    --error-log-path=/var/log/nginx/error.log \
    --http-log-path=/var/log/nginx/access.log \
    --pid-path=/var/run/nginx.pid \
    --with-http_ssl_module \
    --with-http_v2_module \
    --with-http_realip_module \
    --with-http_stub_status_module \
    --with-stream \
    --with-stream_ssl_module \
    --add-module="$BUILD_DIR/ngx_ssl_fingerprint_module"

echo "==> Building nginx (this may take a few minutes)"
make -j"$(nproc)"

echo "==> Installing nginx"
make install

echo "==> Verifying installation"
nginx -V

echo ""
echo "==> Done. nginx installed with JA3/JA4 fingerprint support."
echo ""
echo "    Next steps:"
echo "    1. Copy AI Abyss nginx config:  cp nginx/nginx.conf /etc/nginx/nginx.conf"
echo "    2. Uncomment the fingerprint directives in the config"
echo "    3. Set:  proxy_set_header X-JA3-Hash \$ssl_ja3_hash;"
echo "    4. Test:  nginx -t"
echo "    5. Start: systemctl start nginx"
