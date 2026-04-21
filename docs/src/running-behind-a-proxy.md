# Running behind a reverse proxy

Loggerhead's preferred deployment is as a long-running HTTP server
behind a reverse proxy such as nginx, Apache (with `mod_proxy`), or
Caddy. The proxy handles TLS, logging, access control, and any other
shared concerns for your site.

## nginx

```nginx
location /bzr/ {
    proxy_pass http://127.0.0.1:8080/bzr/;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

And run Loggerhead with a matching `--prefix`:

```sh
loggerhead-serve --prefix=/bzr /srv/bzr
```

## Apache

```apache
<Location "/bzr/">
    ProxyPass http://127.0.0.1:8080/bzr/
    ProxyPassReverse http://127.0.0.1:8080/bzr/
</Location>
```

Again, match `--prefix=/bzr` on the Loggerhead side.

## systemd

A minimal unit:

```ini
[Unit]
Description=Loggerhead
After=network.target

[Service]
ExecStart=/usr/bin/loggerhead-serve --cache-dir=/var/cache/loggerhead /srv/bzr
User=loggerhead
Group=loggerhead
Restart=on-failure

[Install]
WantedBy=multi-user.target
```
