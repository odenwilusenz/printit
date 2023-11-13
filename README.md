

## printit
this was a fun experimante in the 2023 ccc camp, people printed a lot of stickers.

live at > https://eady3rrvez3u.zrok.yair.cc/ 

it currntly a mini obsession. it can do a few things and more to come.   
 * print images (dithered as its a b/w thing)
 * print text
 * print text2image using stable diffusion API

original readme below, this is a fork of [brother_ql_web](https://github.com/pklaus/brother_ql_web)  
both upstream and [printer driver](https://github.com/pklaus/brother_ql) by pklaus  !!

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

we use the zrok.io to secure a static url. 
```bash
zrok reserve public --backend-mode proxy 4678
zrok share reserved kjvrml0bxatq
```
you can also run a service for this. 

## brother\_ql\_web

This is a web service to print labels on Brother QL label printers.

You need Python 3 for this software to work.

![Screenshot](./static/images/screenshots/Label-Designer_Desktop.png)

The web interface is [responsive](https://en.wikipedia.org/wiki/Responsive_web_design).
There's also a screenshot showing [how it looks on a smartphone](./static/images/screenshots/Label-Designer_Phone.png)

### Installation

**ProTip™**: If you know how to use Docker, you might want to use my ready-to-use Docker image to deploy this software.
It can be found [on the Docker hub](https://hub.docker.com/r/pklaus/brother_ql_web/).  
Otherwise, follow the instructions below.

Get the code:

    git clone https://github.com/pklaus/brother_ql_web.git

or download [the ZIP file](https://github.com/pklaus/brother_ql_web/archive/master.zip) and unpack it.

Install the requirements:

    pip install -r requirements.txt

In addition, `fontconfig` should be installed on your system. It's used to identify and
inspect fonts on your machine. This package is pre-installed on many Linux distributions.
If you're using a Mac, I recommend to use [Homebrew](https://brew.sh) to install
fontconfig using [`brew install fontconfig`](http://brewformulas.org/Fontconfig).

### Configuration file

Copy `config.example.json` to `config.json` (e.g. `cp config.example.json config.json`) and adjust the values to match your needs.

### Startup

To start the server, run `./brother_ql_web.py`. The command line parameters overwrite the values configured in `config.json`. Here's its command line interface:

    usage: brother_ql_web.py [-h] [--port PORT] [--loglevel LOGLEVEL]
                             [--font-folder FONT_FOLDER]
                             [--default-label-size DEFAULT_LABEL_SIZE]
                             [--default-orientation {standard,rotated}]
                             [--model {QL-500,QL-550,QL-560,QL-570,QL-580N,QL-650TD,QL-700,QL-710W,QL-720NW,QL-1050,QL-1060N}]
                             [printer]
    
    This is a web service to print labels on Brother QL label printers.
    
    positional arguments:
      printer               String descriptor for the printer to use (like
                            tcp://192.168.0.23:9100 or file:///dev/usb/lp0)
    
    optional arguments:
      -h, --help            show this help message and exit
      --port PORT
      --loglevel LOGLEVEL
      --font-folder FONT_FOLDER
                            folder for additional .ttf/.otf fonts
      --default-label-size DEFAULT_LABEL_SIZE
                            Label size inserted in your printer. Defaults to 62.
      --default-orientation {standard,rotated}
                            Label orientation, defaults to "standard". To turn
                            your text by 90°, state "rotated".
      --model {QL-500,QL-550,QL-560,QL-570,QL-580N,QL-650TD,QL-700,QL-710W,QL-720NW,QL-1050,QL-1060N}
                            The model of your printer (default: QL-500)

### Usage

Once it's running, access the web interface by opening the page with your browser.
If you run it on your local machine, go to <http://localhost:8013> (You can change
the default port 8013 using the --port argument).
You will then be forwarded by default to the interactive web gui located at `/labeldesigner`.

All in all, the web server offers:

* a Web GUI allowing you to print your labels at `/labeldesigner`,
* an API at `/api/print/text?text=Your_Text&font_size=100&font_family=Minion%20Pro%20(%20Semibold%20)`
  to print a label containing 'Your Text' with the specified font properties.


### License

This software is published under the terms of the GPLv3, see the LICENSE file in the repository.

Parts of this package are redistributed software products from 3rd parties. They are subject to different licenses:

* [Bootstrap](https://github.com/twbs/bootstrap), MIT License
* [Glyphicons](https://getbootstrap.com/docs/3.3/components/#glyphicons), MIT License (as part of Bootstrap 3.3)
* [jQuery](https://github.com/jquery/jquery), MIT License
