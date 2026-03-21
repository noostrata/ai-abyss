#!/usr/bin/env bash
# AI Abyss — Proof of Concept (2026)
# https://github.com/terrorswift/ai-abyss
# Build nginx from source with JA3/JA4 TLS fingerprint module.
# Optional — all other features work without this.

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

echo "==> Cloning TLS fingerprint module"
git clone "$FINGERPRINT_MODULE_REPO" ngx_ssl_fingerprint_module

echo "==> Configuring nginx"
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

echo "==> Building"
make -j"$(nproc)"

echo "==> Installing"
make install

echo "==> Verifying installation"
if ! nginx -V 2>&1 | grep -q "ngx_ssl_fingerprint_module"; then
    echo "ERROR: nginx installed but fingerprint module not detected." >&2
    echo "       Check the build output above for errors." >&2
    exit 1
fi

echo ""
echo "==> Done. nginx installed with JA3/JA4 fingerprint support."
echo ""
echo "    Next steps:"
echo "    1. Copy AI Abyss nginx config:  cp nginx/nginx.conf /etc/nginx/nginx.conf"
echo "    2. Replace yourdomain.com with your actual domain"
echo "    3. Uncomment the fingerprint directives"
echo "    4. Set:  proxy_set_header X-JA3-Hash \$ssl_ja3_hash;"
echo "    5. Test:  nginx -t"
echo "    6. Start: systemctl start nginx"
