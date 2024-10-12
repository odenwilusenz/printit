

## printit
this was a fun experimante in the 2023 ccc camp, people printed a lot of stickers.

live at > https://eady3rrvez3u.zrok.yair.cc/ 

it currntly a mini obsession. it can do a few things and more to come.   
 * print images (dithered as its a b/w thing)
 * print text/labels
 * print masks for PCB DIY etching(!), use the transparent ones for best resualts
 * print text2image using stable diffusion API

started as a fork of [brother_ql_web](https://github.com/pklaus/brother_ql_web) and his brother_ql [printer driver](https://github.com/matmair/brother_ql-inventree), this driver is maintained and developed by matmair 

network access by the openziti/zrok projects
### TBD
 * better text/label handeling
   * wrap text for printing paragraphs
   * rotate labels to print bigger stuff
 * convert and print QR codes for URL
 * ???
 * profit
 * 


![print station](./assets/station_sm.jpg)
### usage
added `streamlit`` to requirements.txt
```bash
pip install -r requirements.txt
streamlit run printit.py --server.port 8989
```
```
we use the zrok.io to secure a static url. 
```bash
zrok reserve public --backend-mode proxy 8989
zrok share reserved xxxxxx
```


### systemd
add you service to keep it alive. 

create at `/etc/systemd/system/sticker_zrok.service`
```bash
[Unit]
Description=sticker factory and Zrok Service
After=network.target

[Service]
ExecStart=/bin/bash -c 'source /home/<user>/brother_ql_web/venv/bin/activate && streamlit run printit.py --server.port 8989 & zrok
   share reserved --headless eazrh3dn570q '
WorkingDirectory=/home/<user>/brother_ql_web
Environment="PATH=/home/devdesk/yair/brother_ql_web/venv/bin/python"
Restart=always
User=devdesk
Group=devdesk
[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl deamon-reload
sudo systemctl enable sticker_zrok.service
sudo systemctl start sticker_zrok.service

#debug using
sudo journalctl -u sticker_zrok.service --follow
sudo journalctl -u botprint_zrok.service --follow

```

## botprint
this was a fun experimante in the 2023 ccc camp.   
people printed a lot of stickers in 5 days.

### usage
added `flask`` to requirements.txt

```bash
pip install -r requirements.txt
python botprint.py
```

test using
```bash

uri="https://kjvrml0bxatq.share.zrok.io/api/print/image"
imagepath="output.png"
curl -F "image=@${imagepath}" ${uri}

```

we use the [zrok.io](https://docs.zrok.io/docs/guides/install/linux/) to secure a static url. 
```bash
zrok reserve public --backend-mode proxy 8988
zrok share reserved kjvrml0bxatq
```
you can also run a service for this. 

### License

This software is published under the terms of the GPLv3, see the LICENSE file in the repository.

Parts of this package are redistributed software products from 3rd parties. They are subject to different licenses:

* [Bootstrap](https://github.com/twbs/bootstrap), MIT License
* [Glyphicons](https://getbootstrap.com/docs/3.3/components/#glyphicons), MIT License (as part of Bootstrap 3.3)
* [jQuery](https://github.com/jquery/jquery), MIT License
